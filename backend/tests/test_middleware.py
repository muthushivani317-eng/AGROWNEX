"""Security middleware tests (Phase 2): headers, request-id, body-size, rate limit."""
from __future__ import annotations

from app.core.middleware import (
    BodySizeLimitMiddleware,
    InMemoryRateLimiter,
    RateLimitMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _app(*, limit: int = 1000, max_bytes: int = 100) -> FastAPI:
    app = FastAPI()

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    @app.post("/upload")
    async def upload():
        return {"ok": True}

    # Registered inner→outer; RequestID added last so it wraps everything.
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=max_bytes)
    app.add_middleware(
        RateLimitMiddleware,
        limiter=InMemoryRateLimiter(),
        default_limit=limit,
        auth_limit=limit,
        window=60,
        auth_prefixes=("/auth",),
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIDMiddleware)
    return app


def test_security_and_request_id_headers_present():
    client = TestClient(_app())
    res = client.get("/ping")
    assert res.status_code == 200
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert res.headers["Referrer-Policy"] == "no-referrer"
    assert res.headers["X-Request-ID"]


def test_incoming_request_id_is_preserved():
    client = TestClient(_app())
    res = client.get("/ping", headers={"X-Request-ID": "trace-abc"})
    assert res.headers["X-Request-ID"] == "trace-abc"


def test_oversized_body_rejected_with_413():
    client = TestClient(_app(max_bytes=100))
    res = client.post("/upload", content=b"x" * 200)
    assert res.status_code == 413
    body = res.json()
    assert body["error_code"] == "payload_too_large"
    assert "/" in body["message"]  # Tamil + English


def test_rate_limit_returns_429_after_limit():
    client = TestClient(_app(limit=2))
    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 200
    res = client.get("/ping")  # third hit in the window
    assert res.status_code == 429
    assert res.json()["error_code"] == "rate_limited"
    assert "Retry-After" in res.headers
