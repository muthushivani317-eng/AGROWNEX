"""AgrowNex price relay.

Government mandi-price sites (data.gov.in, eNAM — both hosted by NIC) reset
connections from non-Indian addresses, so our Railway worker (US) cannot reach
them. This tiny service runs on Cloud Run in Mumbai and forwards the worker's
requests to an allow-listed set of hosts only.

Protocol (POST /fetch, ``Authorization: Bearer <RELAY_TOKEN>``)::

    {"method": "GET"|"POST", "url": "https://...", "headers": {...},
     "body_b64": "<base64>" | null}

Success: the upstream status code, body and content type are passed through,
with ``x-relay-upstream: 1``. Relay-side failures (upstream unreachable,
timeout, too large) return 502 with ``x-relay-error`` so the caller can treat
them as a transport error and retry.
"""
from __future__ import annotations

import base64
import binascii
import hmac
import logging
import os
import time
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger("price-relay")

RELAY_TOKEN = os.getenv("RELAY_TOKEN", "")
ALLOWED_HOSTS = frozenset(
    h.strip().lower()
    for h in os.getenv(
        "RELAY_ALLOWED_HOSTS", "api.data.gov.in,enam.gov.in,www.enam.gov.in"
    ).split(",")
    if h.strip()
)
UPSTREAM_TIMEOUT_SECONDS = float(os.getenv("RELAY_UPSTREAM_TIMEOUT_SECONDS", "60"))
MAX_RESPONSE_BYTES = int(os.getenv("RELAY_MAX_RESPONSE_BYTES", str(25 * 1024 * 1024)))
MAX_REQUEST_BODY_BYTES = 64 * 1024

# Headers the caller may set upstream; everything else is dropped.
_FORWARD_HEADERS = frozenset(
    {"accept", "accept-language", "content-type", "referer", "user-agent", "x-requested-with", "origin"}
)

_client = httpx.AsyncClient(
    timeout=httpx.Timeout(UPSTREAM_TIMEOUT_SECONDS),
    follow_redirects=False,
    limits=httpx.Limits(max_connections=20, max_keepalive_connections=5),
)


@asynccontextmanager
async def _lifespan(_: FastAPI):
    yield
    await _client.aclose()


app = FastAPI(
    title="AgrowNex price relay", docs_url=None, redoc_url=None, openapi_url=None, lifespan=_lifespan
)


class FetchRequest(BaseModel):
    method: str = Field(pattern=r"^(GET|POST)$")
    url: str = Field(max_length=4096)
    headers: dict[str, str] = Field(default_factory=dict)
    body_b64: str | None = Field(default=None, max_length=MAX_REQUEST_BODY_BYTES * 2)


def _relay_error(status: int, code: str) -> JSONResponse:
    return JSONResponse({"relay_error": code}, status_code=status, headers={"x-relay-error": code})


def _authorized(request: Request) -> bool:
    if not RELAY_TOKEN:
        return False  # fail closed: never run as an open proxy
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    return scheme.lower() == "bearer" and hmac.compare_digest(token.strip(), RELAY_TOKEN)


def _allowed_url(url: str) -> bool:
    parts = urlsplit(url)
    return (
        parts.scheme == "https"
        and (parts.hostname or "").lower() in ALLOWED_HOSTS
        and parts.port in (None, 443)
        and not parts.username
        and not parts.password
    )


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/fetch")
async def fetch(request: Request, payload: FetchRequest) -> Response:
    if not _authorized(request):
        return _relay_error(401, "unauthorized")
    if not _allowed_url(payload.url):
        return _relay_error(403, "host_not_allowed")
    try:
        body = base64.b64decode(payload.body_b64, validate=True) if payload.body_b64 else None
    except (binascii.Error, ValueError):
        return _relay_error(400, "invalid_body")
    if body is not None and len(body) > MAX_REQUEST_BODY_BYTES:
        return _relay_error(413, "request_too_large")

    headers = {k.lower(): v for k, v in payload.headers.items() if k.lower() in _FORWARD_HEADERS}
    host = urlsplit(payload.url).hostname
    started = time.perf_counter()
    try:
        async with _client.stream(payload.method, payload.url, headers=headers, content=body) as upstream:
            chunks: list[bytes] = []
            size = 0
            async for chunk in upstream.aiter_bytes():
                size += len(chunk)
                if size > MAX_RESPONSE_BYTES:
                    logger.warning("host=%s outcome=too_large", host)
                    return _relay_error(502, "response_too_large")
                chunks.append(chunk)
            status = upstream.status_code
            content_type = upstream.headers.get("content-type", "application/octet-stream")
    except httpx.TimeoutException:
        logger.warning("host=%s outcome=timeout ms=%s", host, round((time.perf_counter() - started) * 1000))
        return _relay_error(502, "upstream_timeout")
    except httpx.HTTPError as exc:
        logger.warning("host=%s outcome=transport_error error=%s", host, type(exc).__name__)
        return _relay_error(502, "upstream_unreachable")

    # Never log query strings: data.gov.in carries the API key there.
    logger.info(
        "host=%s status=%s bytes=%s ms=%s", host, status, size, round((time.perf_counter() - started) * 1000)
    )
    return Response(
        content=b"".join(chunks),
        status_code=status,
        media_type=content_type,
        headers={"x-relay-upstream": "1"},
    )
