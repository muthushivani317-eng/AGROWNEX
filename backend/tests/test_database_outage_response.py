"""A database outage answers 503 + Retry-After (app shows "try again"), never a 500."""
from __future__ import annotations

import httpx
from fastapi import FastAPI
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError

from app.api.errors import register_exception_handlers


def _app(exc: Exception) -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    async def boom():
        raise exc

    return app


async def _get(app):
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        return await c.get("/boom")


async def test_connection_refused_is_503():
    res = await _get(_app(OperationalError("SELECT 1", {}, ConnectionRefusedError())))
    assert res.status_code == 503
    assert res.json()["error_code"] == "SERVICE_TEMPORARILY_UNAVAILABLE"
    assert res.headers["Retry-After"] == "10"


async def test_pool_exhaustion_is_503():
    assert (await _get(_app(PoolTimeoutError("pool full")))).status_code == 503


async def test_real_bugs_stay_500_and_generic():
    res = await _get(_app(KeyError("secret-internal-detail")))
    assert res.status_code == 500 and "secret-internal-detail" not in res.text
