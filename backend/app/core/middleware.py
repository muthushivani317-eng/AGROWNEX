"""HTTP middleware: request-id, security headers, body-size + rate limiting.

Phase 2 (security & abuse protection, docs/SECURITY.md). Rate limiting is a
sliding window backed by Redis in production (shared across workers) with an
in-process fallback for dev/tests; it fails **open** on cache trouble so a Redis
blip never locks farmers out. 429/413 responses use the standard error envelope
with a Tamil-first + English message.
"""
from __future__ import annotations

import time
import uuid
from typing import Protocol

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.response import ErrorResponse

logger = get_logger("core.middleware")

# Tamil-first, English second (product rule 3). Kept here so both the middleware
# and the AI daily-quota guard speak with one voice.
RATE_LIMIT_MESSAGE = (
    "அதிகப்படியான கோரிக்கைகள். சிறிது நேரம் கழித்து மீண்டும் முயற்சிக்கவும். "
    "/ Too many requests. Please wait a moment and try again."
)
PAYLOAD_TOO_LARGE_MESSAGE = (
    "படம்/கோப்பு மிகப் பெரியது. சிறிய படத்தை அனுப்பவும். "
    "/ The file is too large. Please send a smaller image."
)


def _envelope(request: Request, *, status_code: int, message: str, error_code: str) -> JSONResponse:
    body = ErrorResponse(
        message=message,
        error_code=error_code,
        request_id=getattr(request.state, "request_id", ""),
    )
    return JSONResponse(status_code=status_code, content=body.model_dump())


# --------------------------------------------------------------------------- #
# Rate limiters (sliding window)
# --------------------------------------------------------------------------- #
class RateLimiter(Protocol):
    def hit(self, key: str, *, limit: int, window: int) -> tuple[bool, int]:
        """Record a hit; return (allowed, retry_after_seconds)."""
        ...


class InMemoryRateLimiter:
    """Process-local sliding window (dev/tests, single worker)."""

    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = {}

    def hit(self, key: str, *, limit: int, window: int) -> tuple[bool, int]:
        now = time.monotonic()
        bucket = [t for t in self._hits.get(key, []) if t > now - window]
        if len(bucket) >= limit:
            self._hits[key] = bucket
            retry = int(window - (now - bucket[0])) + 1
            return False, max(retry, 1)
        bucket.append(now)
        self._hits[key] = bucket
        return True, 0


class RedisRateLimiter:
    """Redis sliding window via a per-key sorted set; fails open on trouble."""

    def __init__(self, client: object) -> None:
        self._client = client

    def hit(self, key: str, *, limit: int, window: int) -> tuple[bool, int]:
        now = time.time()
        try:
            pipe = self._client.pipeline()  # type: ignore[attr-defined]
            pipe.zremrangebyscore(key, 0, now - window)
            pipe.zadd(key, {f"{now}:{uuid.uuid4().hex}": now})
            pipe.zcard(key)
            pipe.expire(key, window)
            _, _, count, _ = pipe.execute()
        except Exception as exc:  # noqa: BLE001 - never lock farmers out on cache trouble
            logger.warning("redis rate limiter failed (%s); allowing request", exc)
            return True, 0
        if int(count) > limit:
            return False, window
        return True, 0


def build_rate_limiter() -> RateLimiter:
    if settings.cache_backend.lower() == "redis":
        try:  # pragma: no cover - exercised only with a real Redis
            import redis

            client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
            logger.info("rate limiter backend: redis")
            return RedisRateLimiter(client)
        except Exception as exc:  # noqa: BLE001
            logger.warning("redis rate limiter unavailable (%s); using in-memory", exc)
    return InMemoryRateLimiter()


# --------------------------------------------------------------------------- #
# Middleware
# --------------------------------------------------------------------------- #
class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a request id to every request/response for tracing + error envelopes."""

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Baseline hardening headers (docs/SECURITY.md)."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if settings.is_production:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject oversized uploads via Content-Length before reading the body."""

    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.max_bytes:
                    return _envelope(
                        request,
                        status_code=413,
                        message=PAYLOAD_TOO_LARGE_MESSAGE,
                        error_code="payload_too_large",
                    )
            except ValueError:
                pass
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-client sliding-window rate limit (stricter on auth endpoints)."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        limiter: RateLimiter,
        default_limit: int,
        auth_limit: int,
        window: int,
        auth_prefixes: tuple[str, ...],
    ) -> None:
        super().__init__(app)
        self.limiter = limiter
        self.default_limit = default_limit
        self.auth_limit = auth_limit
        self.window = window
        self.auth_prefixes = auth_prefixes

    def _client(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        is_auth = any(path.startswith(p) for p in self.auth_prefixes)
        limit = self.auth_limit if is_auth else self.default_limit
        key = f"rl:{'auth' if is_auth else 'def'}:{self._client(request)}"
        allowed, retry_after = self.limiter.hit(key, limit=limit, window=self.window)
        if not allowed:
            response = _envelope(
                request,
                status_code=429,
                message=RATE_LIMIT_MESSAGE,
                error_code="rate_limited",
            )
            response.headers["Retry-After"] = str(retry_after)
            return response
        return await call_next(request)
