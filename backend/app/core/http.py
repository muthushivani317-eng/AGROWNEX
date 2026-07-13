"""Shared async HTTP client (Phase 3 — connection reuse).

A single process-wide ``httpx.AsyncClient`` with connection pooling, reused by
every outbound provider (Gemini chat/vision, Open-Meteo, Agmarknet) instead of
creating — and tearing down — a new client and TCP/TLS connection per request.
The client is closed on FastAPI shutdown via the app lifespan.

Per-call timeouts are still honored: pass ``timeout=`` to the individual
request; the shared client only sets a default and the connection limits.
"""
from __future__ import annotations

import httpx

_DEFAULT_TIMEOUT = httpx.Timeout(30.0)
_LIMITS = httpx.Limits(max_connections=50, max_keepalive_connections=10)

_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """Return the shared pooled client, lazily creating it once."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT, limits=_LIMITS)
    return _client


async def close_http_client() -> None:
    """Close the shared client (called on app shutdown)."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None
