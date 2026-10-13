"""Plan 2 backup ingest + plan 3 freshness status (HTTP contract, in-memory DB)."""
from __future__ import annotations

from datetime import timedelta

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.api.errors import register_exception_handlers
from app.core.database import get_session
from app.core.timezone import today_ist
from app.modules.market import backup as backup_module
from app.modules.market.models import MarketPrice
from app.modules.market.router import router

TOKEN = "test-ingest-token-" + "x" * 32  # fixture, not a secret


def _report():
    row = {"variety": "Other", "minimumPrice": 1900.0, "maximumPrice": 2200.0,
           "modalPrice": 2050.0, "unitOfPrice": "Rs./Quintal"}
    coconut = {**row, "unitOfPrice": "Rs./Nos"}
    return {"success": True, "markets": [
        {"marketName": "Kallakurichi  APMC", "commodityGroups": [
            {"groupName": "Cereals", "commodities": [
                {"commodityName": "Paddy(Common)", "data": [row]},
                {"commodityName": "Coconut", "data": [coconut]},
            ]}]},
    ]}


@pytest.fixture()
def app(db_session, monkeypatch):
    monkeypatch.setattr(backup_module, "MARKET_INGEST_TOKEN", TOKEN)
    application = FastAPI()
    register_exception_handlers(application)
    application.include_router(router)

    async def _session():
        yield db_session

    application.dependency_overrides[get_session] = _session
    return application


async def _call(app, method, path, **kwargs):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        return await c.request(method, path, **kwargs)


def _body(day=None):
    return {"state": "Tamil Nadu", "trade_day": (day or today_ist() - timedelta(days=1)).isoformat(),
            "report": _report(), "districts": {"kallakurichi apmc": "Kallakurichi"}}


async def test_ingest_stores_official_quintal_rows_with_district(app, db_session):
    res = await _call(app, "POST", "/market/backup/ingest", json=_body(),
                      headers={"X-Market-Ingest-Token": TOKEN})

    assert res.status_code == 200, res.text
    assert res.json()["data"]["saved"] == 1  # coconut (per nut) skipped
    (price,) = (await db_session.execute(select(MarketPrice))).scalars().all()
    assert (price.commodity, price.source, price.modal_price) == ("Paddy(Common)", "agmarknet_v2", 2050)


@pytest.mark.parametrize("headers", [{}, {"X-Market-Ingest-Token": "wrong"}])
async def test_ingest_rejects_missing_or_wrong_token(app, headers):
    res = await _call(app, "POST", "/market/backup/ingest", json=_body(), headers=headers)
    assert res.status_code == 401


async def test_ingest_is_disabled_without_configured_token(app, monkeypatch):
    monkeypatch.setattr(backup_module, "MARKET_INGEST_TOKEN", "")
    res = await _call(app, "POST", "/market/backup/ingest", json=_body(),
                      headers={"X-Market-Ingest-Token": ""})
    assert res.status_code == 401


@pytest.mark.parametrize("days", [-1, 8])
async def test_ingest_rejects_future_or_old_reports(app, days):
    res = await _call(app, "POST", "/market/backup/ingest",
                      json=_body(today_ist() - timedelta(days=days)),
                      headers={"X-Market-Ingest-Token": TOKEN})
    assert res.status_code == 422


async def test_ingest_rejects_report_without_usable_prices(app):
    body = _body()
    body["report"] = {"markets": []}
    res = await _call(app, "POST", "/market/backup/ingest", json=body,
                      headers={"X-Market-Ingest-Token": TOKEN})
    assert res.status_code == 422


async def test_sync_status_reports_stale_then_fresh(app):
    empty = (await _call(app, "GET", "/market/sync-status")).json()["data"]
    assert empty["latest_price_date"] is None and empty["stale"] is True

    await _call(app, "POST", "/market/backup/ingest", json=_body(),
                headers={"X-Market-Ingest-Token": TOKEN})
    status = (await _call(app, "GET", "/market/sync-status?state=Tamil Nadu")).json()["data"]

    assert status["stale"] is False
    assert status["days_old"] == 1
    assert status["prices_on_latest_date"] == 1
    assert status["sources_on_latest_date"] == [{"source": "agmarknet_v2", "prices": 1}]


async def test_ingest_refuses_a_short_configured_token(app, monkeypatch):
    monkeypatch.setattr(backup_module, "MARKET_INGEST_TOKEN", "short")
    res = await _call(app, "POST", "/market/backup/ingest", json=_body(),
                      headers={"X-Market-Ingest-Token": "short"})
    assert res.status_code == 401


def _datagov_body(day):
    d = day.strftime("%d/%m/%Y")
    row = {"state": "Tamil Nadu", "district": "Salem", "market": "Salem(Uzhavar Sandhai)",
           "commodity": "Tomato", "variety": "Local", "grade": "FAQ", "arrival_date": d,
           "min_price": "1800", "max_price": "2200", "modal_price": "2000"}
    other_state = {**row, "state": "Kerala"}
    other_day = {**row, "arrival_date": (day - timedelta(days=1)).strftime("%d/%m/%Y")}
    no_date = {**row, "arrival_date": ""}
    return {"state": "Tamil Nadu", "trade_day": day.isoformat(),
            "records": [row, other_state, other_day, no_date]}


async def test_ingest_stores_datagov_records_for_state_and_day_only(app, db_session):
    day = today_ist() - timedelta(days=1)
    res = await _call(app, "POST", "/market/backup/ingest", json=_datagov_body(day),
                      headers={"X-Market-Ingest-Token": TOKEN})

    assert res.status_code == 200, res.text
    assert res.json()["data"]["saved"] == 1
    (price,) = (await db_session.execute(select(MarketPrice))).scalars().all()
    assert (price.commodity, price.source, price.modal_price, price.price_date) == ("Tomato", "agmarknet", 2000, day)


@pytest.mark.parametrize("change", ["neither", "both"])
async def test_ingest_needs_exactly_one_source(app, change):
    body = _body()
    if change == "neither":
        body.pop("report")
    else:
        body["records"] = []
    res = await _call(app, "POST", "/market/backup/ingest", json=body,
                      headers={"X-Market-Ingest-Token": TOKEN})
    assert res.status_code in (400, 422)
