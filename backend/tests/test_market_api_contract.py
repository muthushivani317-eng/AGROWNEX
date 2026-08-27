"""HTTP contract tests for market-data outage handling."""
from __future__ import annotations

from unittest.mock import Mock

import httpx
from app.api.errors import register_exception_handlers
from app.modules.auth.dependencies import get_current_user
from app.modules.market.dependencies import get_market_service
from app.modules.market.exceptions import MarketDataUnavailableError
from app.modules.market.router import router
from fastapi import FastAPI


class _UnavailableMarketService:
    async def get_prices(self, filters, *, today_only: bool = False):
        raise MarketDataUnavailableError()


def _app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: Mock(id="farmer-id")
    app.dependency_overrides[get_market_service] = _UnavailableMarketService
    return app


async def test_market_provider_outage_uses_retryable_structured_503() -> None:
    transport = httpx.ASGITransport(app=_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/market")

    assert response.status_code == 503
    assert response.json()["success"] is False
    assert response.json()["error_code"] == "market_data_unavailable"
    assert "temporarily unavailable" in response.json()["message"]
