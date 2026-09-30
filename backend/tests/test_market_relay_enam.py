"""India price relay transport, eNAM second source, fallback and dual-source sync.

No network: upstreams (the relay, eNAM, data.gov.in) are httpx.MockTransport.
"""
from __future__ import annotations

import base64
import json
from datetime import date
from urllib.parse import parse_qs

import httpx
import pytest
from sqlalchemy import select

from app.modules.market import enam as enam_module
from app.modules.market import jobs as jobs_module
from app.modules.market import provider as provider_module
from app.modules.market.enam import EnamProvider, parse_enam_record
from app.modules.market.exceptions import MarketDataUnavailableError
from app.modules.market.models import MarketPrice
from app.modules.market.provider import (
    AgmarknetProvider,
    FallbackMarketProvider,
    PriceQuery,
    ProviderPrice,
)
from app.modules.market.relay import RelayTransport

TODAY = date(2026, 10, 1)


def _enam_row(**overrides):
    row = {
        "state": "TAMIL NADU",
        "apmc": "THANJAVUR",
        "commodity": "PADDY",
        "min_price": "1900",
        "modal_price": "2050",
        "max_price": "2200",
        "Commodity_Uom": "Qui",
        "created_at": "2026-09-30",
    }
    row.update(overrides)
    return row


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


# --------------------------------------------------------------------------- #
# eNAM parsing
# --------------------------------------------------------------------------- #
def test_parse_enam_record_normalizes_case_units_and_date():
    price = parse_enam_record(_enam_row(), trade_day=TODAY)
    assert price is not None
    assert (price.commodity, price.market, price.state) == ("Paddy", "Thanjavur", "Tamil Nadu")
    assert (price.minimum_price, price.modal_price, price.maximum_price) == (1900, 2050, 2200)
    assert price.unit == "quintal"
    assert price.source == "enam"
    assert price.price_date == date(2026, 9, 30)


def test_parse_enam_record_skips_non_quintal_and_priceless_rows():
    assert parse_enam_record(_enam_row(Commodity_Uom="Nos"), trade_day=TODAY) is None
    assert parse_enam_record(
        _enam_row(min_price="0", modal_price="", max_price=None), trade_day=TODAY
    ) is None
    assert parse_enam_record(_enam_row(commodity=""), trade_day=TODAY) is None


def test_parse_enam_record_fills_missing_bounds_from_modal():
    price = parse_enam_record(_enam_row(min_price="", max_price=""), trade_day=TODAY)
    assert price is not None
    assert price.minimum_price == price.maximum_price == price.modal_price == 2050


# --------------------------------------------------------------------------- #
# eNAM provider
# --------------------------------------------------------------------------- #
async def test_enam_walks_back_to_latest_day_with_trades_and_filters(monkeypatch):
    seen_days: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
        assert form["stateName"] == "TAMIL NADU"
        assert form["commodityName"] == "-- Select Commodity --"
        assert request.headers["x-requested-with"] == "XMLHttpRequest"
        seen_days.append(form["fromDate"])
        if form["fromDate"] == "2026-10-01":
            return httpx.Response(200, json={"data": []})
        return httpx.Response(
            200,
            json={"data": [_enam_row(), _enam_row(commodity="BANANA", apmc="TRICHY")]},
        )

    monkeypatch.setattr(enam_module, "get_market_http_client", lambda: _client(handler))
    provider = EnamProvider(today=TODAY, max_retries=1)

    prices = await provider.fetch_prices(PriceQuery(commodity="paddy", state="Tamil Nadu"))

    assert seen_days == ["2026-10-01", "2026-09-30"]
    assert [p.commodity for p in prices] == ["Paddy"]


async def test_enam_unreachable_raises_unavailable(monkeypatch):
    def handler(request):
        raise httpx.ConnectError("reset", request=request)

    monkeypatch.setattr(enam_module, "get_market_http_client", lambda: _client(handler))
    monkeypatch.setattr(enam_module.asyncio, "sleep", _no_sleep)
    with pytest.raises(MarketDataUnavailableError):
        await EnamProvider(today=TODAY, max_retries=2, lookback_days=2).fetch_prices(PriceQuery())


async def test_enam_reachable_but_no_trades_returns_empty(monkeypatch):
    monkeypatch.setattr(
        enam_module,
        "get_market_http_client",
        lambda: _client(lambda r: httpx.Response(200, json={"data": []})),
    )
    assert await EnamProvider(today=TODAY, lookback_days=2).fetch_prices(PriceQuery()) == []


async def test_enam_non_json_is_retried_then_unavailable(monkeypatch):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(200, text="<html>maintenance</html>")

    monkeypatch.setattr(enam_module, "get_market_http_client", lambda: _client(handler))
    monkeypatch.setattr(enam_module.asyncio, "sleep", _no_sleep)
    with pytest.raises(MarketDataUnavailableError):
        await EnamProvider(today=TODAY, max_retries=2, lookback_days=1).fetch_prices(PriceQuery())
    assert calls["n"] == 2


async def _no_sleep(_seconds):
    return None


# --------------------------------------------------------------------------- #
# Relay transport
# --------------------------------------------------------------------------- #
async def test_relay_transport_wraps_request_and_returns_upstream_reply():
    captured: dict = {}

    def relay(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers["authorization"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"records": []},
            headers={"x-relay-upstream": "1", "content-type": "application/json"},
        )

    transport = RelayTransport(
        "https://relay.example.run.app/", "tok", inner=httpx.MockTransport(relay)
    )
    async with httpx.AsyncClient(transport=transport) as client:
        res = await client.post(
            "https://enam.gov.in/web/Ajax_ctrl/trade_data_list",
            data={"a": "1"},
            headers={"Referer": "https://enam.gov.in/", "Cookie": "x"},
        )

    assert res.status_code == 200 and res.json() == {"records": []}
    assert captured["url"] == "https://relay.example.run.app/fetch"
    assert captured["auth"] == "Bearer tok"
    payload = captured["payload"]
    assert payload["method"] == "POST"
    assert payload["url"] == "https://enam.gov.in/web/Ajax_ctrl/trade_data_list"
    assert base64.b64decode(payload["body_b64"]) == b"a=1"
    assert payload["headers"]["referer"] == "https://enam.gov.in/"
    assert "cookie" not in {k.lower() for k in payload["headers"]}


@pytest.mark.parametrize("error", ["upstream_unreachable", "upstream_timeout", "unauthorized"])
async def test_relay_errors_become_connect_errors(error):
    transport = RelayTransport(
        "https://relay.example",
        "tok",
        inner=httpx.MockTransport(
            lambda r: httpx.Response(502, headers={"x-relay-error": error})
        ),
    )
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(httpx.ConnectError):
            await client.get("https://api.data.gov.in/resource/x")


async def test_agmarknet_through_relay_end_to_end(monkeypatch):
    upstream_record = {
        "commodity": "Paddy",
        "market": "Thanjavur",
        "district": "Thanjavur",
        "state": "Tamil Nadu",
        "min_price": "1900",
        "max_price": "2100",
        "modal_price": "2000",
        "arrival_date": "30/09/2026",
    }

    def relay(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["url"].startswith("https://api.data.gov.in/resource/")
        return httpx.Response(200, json={"records": [upstream_record]})

    client = httpx.AsyncClient(
        transport=RelayTransport("https://relay.example", "tok", inner=httpx.MockTransport(relay))
    )
    monkeypatch.setattr(provider_module, "get_http_client", lambda: client)

    prices = await AgmarknetProvider(api_key="k", max_retries=1).fetch_prices(PriceQuery())

    assert [(p.commodity, p.modal_price, p.source) for p in prices] == [
        ("Paddy", 2000.0, "agmarknet")
    ]


# --------------------------------------------------------------------------- #
# Fallback
# --------------------------------------------------------------------------- #
def _price(source: str, commodity: str = "Paddy", market: str = "Thanjavur") -> ProviderPrice:
    return ProviderPrice(
        commodity=commodity,
        variety="",
        market=market,
        district="",
        state="Tamil Nadu",
        minimum_price=1900,
        maximum_price=2100,
        modal_price=2000,
        unit="quintal",
        price_date=TODAY,
        source=source,
    )


class _Down:
    source = "agmarknet"

    def __init__(self):
        self.calls = 0

    async def fetch_prices(self, query):
        self.calls += 1
        raise MarketDataUnavailableError()


class _Up:
    def __init__(self, source: str, prices: list[ProviderPrice]):
        self.source = source
        self.prices = prices
        self.calls = 0

    async def fetch_prices(self, query):
        self.calls += 1
        return self.prices

    async def fetch_all_prices(self, query, *, max_pages):
        self.calls += 1
        return self.prices


async def test_fallback_uses_enam_when_agmarknet_unavailable():
    enam = _Up("enam", [_price("enam")])
    result = await FallbackMarketProvider(_Down(), enam).fetch_prices(PriceQuery())
    assert [p.source for p in result] == ["enam"]


async def test_fallback_keeps_a_real_empty_answer_from_primary():
    enam = _Up("enam", [_price("enam")])
    result = await FallbackMarketProvider(_Up("agmarknet", []), enam).fetch_prices(PriceQuery())
    assert result == [] and enam.calls == 0


async def test_fallback_raises_when_every_source_is_down():
    with pytest.raises(MarketDataUnavailableError):
        await FallbackMarketProvider(_Down(), _Down()).fetch_prices(PriceQuery())


def test_default_provider_is_agmarknet_then_enam(monkeypatch):
    monkeypatch.setattr(provider_module, "DATA_GOV_API_KEY", "k")
    monkeypatch.setattr(provider_module, "ENAM_ENABLED", True)
    selected = provider_module.get_default_provider()
    assert isinstance(selected, FallbackMarketProvider)
    assert [p.source for p in selected.providers] == ["agmarknet", "enam"]


# --------------------------------------------------------------------------- #
# Worker: every source synced, one being down doesn't block the other
# --------------------------------------------------------------------------- #
async def test_state_sync_stores_enam_when_agmarknet_is_down(db_session, monkeypatch):
    down = _Down()
    enam = _Up("enam", [_price("enam", "Banana", "Trichy")])
    monkeypatch.setattr(jobs_module, "_sync_sources", lambda: [down, enam])

    result = await refresh(db_session)

    assert result["synced_states"] == 1
    assert result["synced_prices"] == 1
    stored = (await db_session.execute(select(MarketPrice))).scalars().all()
    assert [(p.commodity, p.source) for p in stored] == [("Banana", "enam")]


async def test_state_sync_stores_both_sources_when_both_answer(db_session, monkeypatch):
    agmark = _Up("agmarknet", [_price("agmarknet", "Paddy", "Thanjavur")])
    enam = _Up("enam", [_price("enam", "Banana", "Trichy")])
    monkeypatch.setattr(jobs_module, "_sync_sources", lambda: [agmark, enam])

    result = await refresh(db_session)

    assert result["synced_prices"] == 2
    sources = {p.source for p in (await db_session.execute(select(MarketPrice))).scalars()}
    assert sources == {"agmarknet", "enam"}


async def refresh(db_session):
    return await jobs_module.refresh_market_prices(db_session, sync_states=("Tamil Nadu",))
