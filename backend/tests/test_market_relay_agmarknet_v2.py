"""India price relay transport, Agmarknet 2.0 second source, fallback and
dual-source sync. No network: every upstream is an httpx.MockTransport.
"""
from __future__ import annotations

import base64
import json
from datetime import date

import httpx
import pytest
from sqlalchemy import select

from app.modules.market import agmarknet_v2 as v2_module
from app.modules.market import jobs as jobs_module
from app.modules.market import provider as provider_module
from app.modules.market.agmarknet_v2 import AgmarknetV2Provider, parse_state_report
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

# Shapes copied from the live API (2026-10-01, Tamil Nadu).
STATES = {"status": "success", "states": [
    {"id": 30, "state_name": "Sikkim"},
    {"id": 31, "state_name": "Tamil Nadu"},
]}
DISTRICTS = [
    {"market_id": 1, "market_name": "Kallakurichi  APMC", "district_name": "Kallakurichi", "state_id": 31},
    {"market_id": 2, "market_name": "Kallakurichi APMC", "district_name": "Wrong State", "state_id": 2},
]


def _report(markets):
    return {"success": True, "message": "Data fetched successfully.", "markets": markets}


def _market(name, commodity, *rows, group="Cereals"):
    return {"marketName": name, "commodityGroups": [
        {"groupName": group, "commodities": [{"commodityName": commodity, "data": list(rows)}]}
    ]}


def _row(modal=2050.0, low=1900.0, high=2200.0, unit="Rs./Quintal", variety="Other"):
    return {"arrivals": 1.2, "unitOfArrivals": "Metric Tonnes", "variety": variety,
            "minimumPrice": low, "maximumPrice": high, "modalPrice": modal, "unitOfPrice": unit}


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def _no_sleep(_seconds):
    return None


# --------------------------------------------------------------------------- #
# Agmarknet 2.0 parsing
# --------------------------------------------------------------------------- #
def test_parse_state_report_flattens_markets_and_maps_district():
    payload = _report([
        _market("Kallakurichi APMC", "Bajra(Pearl Millet/Cumbu)", _row()),
        _market("AJattihalli(Uzhavar Sandhai )", "Banana ", _row(8750, 8500, 9000, variety="Red Banana"),
                group="Fruits"),
    ])
    prices = parse_state_report(payload, state="Tamil Nadu", trade_day=TODAY,
                                districts={"kallakurichi apmc": "Kallakurichi"})
    assert [(p.market, p.district, p.commodity, p.variety, p.modal_price) for p in prices] == [
        ("Kallakurichi APMC", "Kallakurichi", "Bajra(Pearl Millet/Cumbu)", "Other", 2050.0),
        ("AJattihalli(Uzhavar Sandhai )", "", "Banana", "Red Banana", 8750.0),
    ]
    assert {p.source for p in prices} == {"agmarknet_v2"}
    assert {p.unit for p in prices} == {"quintal"}
    assert {p.price_date for p in prices} == {TODAY}


def test_parse_state_report_skips_non_quintal_and_priceless_rows():
    payload = _report([_market("M", "Coconut", _row(unit="Rs./Nos"), _row(modal=0, low=None, high=0))])
    assert parse_state_report(payload, state="Tamil Nadu", trade_day=TODAY) == []


def test_parse_state_report_fills_missing_bounds_from_modal():
    payload = _report([_market("M", "Paddy", _row(low=None, high=None))])
    (price,) = parse_state_report(payload, state="Tamil Nadu", trade_day=TODAY)
    assert price.minimum_price == price.maximum_price == price.modal_price == 2050


# --------------------------------------------------------------------------- #
# Agmarknet 2.0 provider
# --------------------------------------------------------------------------- #
def _api(reports: dict[str, dict], seen: list[str] | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["referer"] == "https://agmarknet.gov.in/"
        path = request.url.path
        if path.endswith("/location/state"):
            return httpx.Response(200, json=STATES)
        if path.endswith("/market-district-state"):
            return httpx.Response(200, json=DISTRICTS)
        if path.endswith("/commodity-wise/daily-report-state"):
            assert request.url.params["stateIds"] == "31"
            day = request.url.params["date"]
            if seen is not None:
                seen.append(day)
            return httpx.Response(200, json=reports.get(day, _report([])))
        return httpx.Response(404)
    return handler


async def test_v2_walks_back_to_latest_day_filters_and_maps_district(monkeypatch):
    seen: list[str] = []
    reports = {"2026-09-30": _report([
        _market("Kallakurichi APMC", "Paddy(Common)", _row()),
        _market("Trichy APMC", "Banana", _row(3000)),
    ])}
    monkeypatch.setattr(v2_module, "get_market_http_client", lambda: _client(_api(reports, seen)))

    prices = await AgmarknetV2Provider(today=TODAY, max_retries=1).fetch_prices(
        PriceQuery(commodity="paddy", state="tamil nadu")
    )

    assert seen == ["2026-10-01", "2026-09-30"]
    assert [(p.commodity, p.district, p.state, p.price_date) for p in prices] == [
        ("Paddy(Common)", "Kallakurichi", "Tamil Nadu", date(2026, 9, 30))
    ]


async def test_v2_unknown_state_is_unavailable(monkeypatch):
    monkeypatch.setattr(v2_module, "get_market_http_client", lambda: _client(_api({})))
    with pytest.raises(MarketDataUnavailableError):
        await AgmarknetV2Provider(today=TODAY).fetch_prices(PriceQuery(state="Atlantis"))


async def test_v2_unreachable_raises_unavailable(monkeypatch):
    def handler(request):
        raise httpx.ConnectError("reset", request=request)

    monkeypatch.setattr(v2_module, "get_market_http_client", lambda: _client(handler))
    monkeypatch.setattr(v2_module.asyncio, "sleep", _no_sleep)
    with pytest.raises(MarketDataUnavailableError):
        await AgmarknetV2Provider(today=TODAY, max_retries=2, lookback_days=2).fetch_prices(PriceQuery())


async def test_v2_reachable_but_no_reports_returns_empty(monkeypatch):
    monkeypatch.setattr(v2_module, "get_market_http_client", lambda: _client(_api({})))
    assert await AgmarknetV2Provider(today=TODAY, lookback_days=2).fetch_prices(PriceQuery()) == []


async def test_v2_prices_still_load_when_district_lookup_fails(monkeypatch):
    reports = {"2026-10-01": _report([_market("Kallakurichi APMC", "Paddy", _row())])}
    base = _api(reports)

    def handler(request):
        if request.url.path.endswith("/market-district-state"):
            return httpx.Response(500)
        return base(request)

    monkeypatch.setattr(v2_module, "get_market_http_client", lambda: _client(handler))
    monkeypatch.setattr(v2_module.asyncio, "sleep", _no_sleep)
    (price,) = await AgmarknetV2Provider(today=TODAY, max_retries=1).fetch_prices(PriceQuery())
    assert price.district == ""


async def test_v2_server_error_html_is_retried_then_skipped(monkeypatch):
    calls = {"n": 0}
    base = _api({})

    def handler(request):
        if request.url.path.endswith("/daily-report-state"):
            calls["n"] += 1
            return httpx.Response(500, text="<h1>Server Error (500)</h1>")
        return base(request)

    monkeypatch.setattr(v2_module, "get_market_http_client", lambda: _client(handler))
    monkeypatch.setattr(v2_module.asyncio, "sleep", _no_sleep)
    with pytest.raises(MarketDataUnavailableError):
        await AgmarknetV2Provider(today=TODAY, max_retries=2, lookback_days=1).fetch_prices(PriceQuery())
    assert calls["n"] == 2


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
            "https://api.agmarknet.gov.in/v1/x",
            data={"a": "1"},
            headers={"Referer": "https://agmarknet.gov.in/", "Cookie": "x"},
        )

    assert res.status_code == 200 and res.json() == {"records": []}
    assert captured["url"] == "https://relay.example.run.app/fetch"
    assert captured["auth"] == "Bearer tok"
    payload = captured["payload"]
    assert payload["method"] == "POST"
    assert payload["url"] == "https://api.agmarknet.gov.in/v1/x"
    assert base64.b64decode(payload["body_b64"]) == b"a=1"
    assert payload["headers"]["referer"] == "https://agmarknet.gov.in/"
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


async def test_fallback_uses_v2_when_data_gov_unavailable():
    v2 = _Up("agmarknet_v2", [_price("agmarknet_v2")])
    result = await FallbackMarketProvider(_Down(), v2).fetch_prices(PriceQuery())
    assert [p.source for p in result] == ["agmarknet_v2"]


async def test_fallback_keeps_a_real_empty_answer_from_primary():
    v2 = _Up("agmarknet_v2", [_price("agmarknet_v2")])
    result = await FallbackMarketProvider(_Up("agmarknet", []), v2).fetch_prices(PriceQuery())
    assert result == [] and v2.calls == 0


async def test_fallback_raises_when_every_source_is_down():
    with pytest.raises(MarketDataUnavailableError):
        await FallbackMarketProvider(_Down(), _Down()).fetch_prices(PriceQuery())


def test_default_provider_is_data_gov_then_v2(monkeypatch):
    monkeypatch.setattr(provider_module, "DATA_GOV_API_KEY", "k")
    monkeypatch.setattr(provider_module, "AGMARKNET_V2_ENABLED", True)
    selected = provider_module.get_default_provider()
    assert isinstance(selected, FallbackMarketProvider)
    assert [p.source for p in selected.providers] == ["agmarknet", "agmarknet_v2"]


# --------------------------------------------------------------------------- #
# Worker: every source synced, one being down doesn't block the other
# --------------------------------------------------------------------------- #
async def test_state_sync_stores_v2_when_data_gov_is_down(db_session, monkeypatch):
    down = _Down()
    v2 = _Up("agmarknet_v2", [_price("agmarknet_v2", "Banana", "Trichy")])
    monkeypatch.setattr(jobs_module, "_sync_sources", lambda: [down, v2])

    result = await refresh(db_session)

    assert result["synced_states"] == 1
    assert result["synced_prices"] == 1
    stored = (await db_session.execute(select(MarketPrice))).scalars().all()
    assert [(p.commodity, p.source) for p in stored] == [("Banana", "agmarknet_v2")]


async def test_state_sync_stores_both_sources_when_both_answer(db_session, monkeypatch):
    agmark = _Up("agmarknet", [_price("agmarknet", "Paddy", "Thanjavur")])
    v2 = _Up("agmarknet_v2", [_price("agmarknet_v2", "Banana", "Trichy")])
    monkeypatch.setattr(jobs_module, "_sync_sources", lambda: [agmark, v2])

    result = await refresh(db_session)

    assert result["synced_prices"] == 2
    sources = {p.source for p in (await db_session.execute(select(MarketPrice))).scalars()}
    assert sources == {"agmarknet", "agmarknet_v2"}


async def refresh(db_session):
    return await jobs_module.refresh_market_prices(db_session, sync_states=("Tamil Nadu",))
