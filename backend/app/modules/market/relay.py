"""HTTP client for market providers, optionally routed through the India relay.

data.gov.in and eNAM (both hosted by NIC) reset TCP connections from our
Railway worker's US address. When ``MARKET_RELAY_URL`` is set, every market
provider request is tunnelled through the relay on Cloud Run (Mumbai) — see
``/relay`` at the repo root. Providers keep using a normal ``httpx`` client;
only the transport changes, so their retry/parse logic is untouched.
"""
from __future__ import annotations

import base64

import httpx

from app.core.http import get_http_client
from app.core.logging import get_logger
from app.modules.market.constants import MARKET_RELAY_TOKEN, MARKET_RELAY_URL

logger = get_logger("market.relay")

# Request headers worth forwarding upstream (the relay drops everything else).
_FORWARD = ("accept", "accept-language", "content-type", "referer", "user-agent", "x-requested-with", "origin")


class RelayTransport(httpx.AsyncBaseTransport):
    """Sends each request to ``<relay>/fetch`` and returns the upstream reply.

    A relay-side failure (upstream unreachable/timeout, marked by the
    ``x-relay-error`` header) is raised as ``httpx.ConnectError`` so providers
    treat it exactly like a direct connection failure and retry.
    """

    def __init__(self, relay_url: str, token: str, *, inner: httpx.AsyncBaseTransport | None = None) -> None:
        self._endpoint = f"{relay_url.rstrip('/')}/fetch"
        self._token = token
        self._client = httpx.AsyncClient(
            transport=inner,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=5),
        )

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        body = await request.aread()
        payload = {
            "method": request.method,
            "url": str(request.url),
            "headers": {k: v for k, v in request.headers.items() if k.lower() in _FORWARD},
            "body_b64": base64.b64encode(body).decode() if body else None,
        }
        timeout = request.extensions.get("timeout") or {}
        read_timeout = timeout.get("read") or 60.0
        try:
            relayed = await self._client.post(
                self._endpoint,
                json=payload,
                headers={"Authorization": f"Bearer {self._token}"},
                # Leave headroom for the relay's own upstream call.
                timeout=httpx.Timeout(read_timeout + 15.0, connect=15.0),
            )
        except httpx.TimeoutException as exc:
            raise httpx.ReadTimeout("price relay timed out", request=request) from exc
        except httpx.TransportError as exc:
            raise httpx.ConnectError("price relay unreachable", request=request) from exc

        relay_error = relayed.headers.get("x-relay-error")
        if relay_error:
            if relay_error in {"unauthorized", "host_not_allowed"}:
                # Misconfiguration, not a flaky upstream: make it loud.
                logger.error("price relay rejected request: %s", relay_error)
            raise httpx.ConnectError(f"price relay: {relay_error}", request=request)

        return httpx.Response(
            status_code=relayed.status_code,
            headers={"content-type": relayed.headers.get("content-type", "application/octet-stream")},
            content=relayed.content,
            request=request,
        )

    async def aclose(self) -> None:
        await self._client.aclose()


_relay_client: httpx.AsyncClient | None = None


def relay_enabled() -> bool:
    return bool(MARKET_RELAY_URL and MARKET_RELAY_TOKEN)


def get_market_http_client() -> httpx.AsyncClient:
    """Client for market providers: via the India relay when configured."""
    global _relay_client
    if not relay_enabled():
        return get_http_client()
    if _relay_client is None or _relay_client.is_closed:
        logger.info("market providers routed through India price relay")
        _relay_client = httpx.AsyncClient(transport=RelayTransport(MARKET_RELAY_URL, MARKET_RELAY_TOKEN))
    return _relay_client
