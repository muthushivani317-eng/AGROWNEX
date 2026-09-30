"""Unit tests for market providers (no network — parsing + mock + selection)."""
from __future__ import annotations

import logging
from datetime import date

import httpx
import pytest
from app.modules.market.constants import PriceUnit
from app.modules.market.exceptions import MarketDataUnavailableError
from app.modules.market.provider import (
    AgmarknetProvider,
    MockMarketProvider,
    PriceQuery,
    get_default_provider,
    parse_agmarknet_record,
)


def _record(**overrides: object) -> dict:
    base = {
        "commodity": "Paddy",
        "variety": "Common",
        "grade": "FAQ",
        "market": "Thanjavur",
        "district": "Thanjavur",
        "state": "Tamil Nadu",
        "min_price": "1980",
        "max_price": "2120",
        "modal_price": "2050",
        "arrival_date": "11/07/2026",
    }
    base.update(overrides)
    return base


def test_parse_agmarknet_record_normalizes_fields() -> None:
    price = parse_agmarknet_record(_record())
    assert price is not None
    assert price.commodity == "Paddy"
    assert price.market == "Thanjavur"
    assert price.minimum_price == 1980
    assert price.maximum_price == 2120
    assert price.modal_price == 2050
    assert price.unit == PriceUnit.QUINTAL.value
    assert price.price_date == date(2026, 7, 11)
    assert price.source == "agmarknet"


def test_parse_agmarknet_record_accepts_legacy_government_field_names() -> None:
    price = parse_agmarknet_record(
        {
            "State": "Tamil Nadu",
            "District": "Thanjavur",
            "Market": "Thanjavur",
            "Commodity": "Paddy",
            "Variety": "Common",
            "Grade": "FAQ",
            "Arrival_Date": "22/08/2026",
            "Min_x0020_Price": "1980",
            "Max_x0020_Price": "2120",
            "Modal_x0020_Price": "2050",
        }
    )

    assert price is not None
    assert price.commodity == "Paddy"
    assert price.market == "Thanjavur"
    assert price.district == "Thanjavur"
    assert price.modal_price == 2050
    assert price.price_date == date(2026, 8, 22)


def test_parse_fills_missing_min_max_from_modal() -> None:
    price = parse_agmarknet_record(_record(min_price="0", max_price=""))
    assert price is not None
    assert price.minimum_price == 2050
    assert price.maximum_price == 2050


def test_parse_rejects_record_without_any_price() -> None:
    assert parse_agmarknet_record(_record(min_price="0", max_price="0", modal_price="")) is None


def test_parse_rejects_record_without_commodity_or_market() -> None:
    assert parse_agmarknet_record(_record(commodity="")) is None
    assert parse_agmarknet_record(_record(market="")) is None


def test_parse_falls_back_to_today_on_bad_date() -> None:
    price = parse_agmarknet_record(_record(arrival_date="not-a-date"))
    assert price is not None  # date defaults to today rather than crashing


async def test_mock_provider_filters_by_commodity_and_district() -> None:
    provider = MockMarketProvider(today=date(2026, 7, 11))
    all_prices = await provider.fetch_prices(PriceQuery())
    assert len(all_prices) > 1

    paddy = await provider.fetch_prices(PriceQuery(commodity="paddy"))
    assert paddy and all(p.commodity == "Paddy" for p in paddy)

    salem = await provider.fetch_prices(PriceQuery(district="Salem"))
    assert salem and all(p.district == "Salem" for p in salem)


async def test_mock_provider_respects_limit() -> None:
    provider = MockMarketProvider()
    limited = await provider.fetch_prices(PriceQuery(limit=2))
    assert len(limited) == 2


def test_default_provider_is_unavailable_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    # Missing credentials (and eNAM switched off) must never synthesize
    # farmer-facing prices.
    import app.modules.market.provider as provider_module

    monkeypatch.setattr(provider_module, "ENAM_ENABLED", False)
    provider = get_default_provider()
    assert provider.source == "unavailable"


async def test_agmarknet_failure_logs_sanitized_attempt_metadata(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    secret = "sensitive-data-gov-api-key"
    raw_payload = "upstream-private-response"

    class FailingClient:
        async def get(self, url, **_request_options):
            request = httpx.Request("GET", url)
            return httpx.Response(429, request=request, text=raw_payload)

    monkeypatch.setattr(
        "app.modules.market.provider.get_http_client", lambda: FailingClient()
    )
    provider = AgmarknetProvider(api_key=secret, max_retries=1)

    with caplog.at_level(logging.INFO), pytest.raises(MarketDataUnavailableError):
        await provider.fetch_prices(PriceQuery(commodity="Paddy"))

    rendered = caplog.text
    assert "provider=agmarknet" in rendered
    assert "attempt=1" in rendered
    assert "category=http_status" in rendered
    assert "status=429" in rendered
    assert "latency_ms=" in rendered
    assert secret not in rendered
    assert raw_payload not in rendered


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"records": {"commodity": "Paddy"}},
        {"records": [{"unexpected": "row"}]},
    ],
    ids=["missing-records", "records-not-list", "all-records-invalid"],
)
async def test_agmarknet_schema_failures_are_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    payload: object,
) -> None:
    class SchemaFailureClient:
        async def get(self, url, **_request_options):
            request = httpx.Request("GET", url)
            return httpx.Response(200, request=request, json=payload)

    monkeypatch.setattr(
        "app.modules.market.provider.get_http_client", lambda: SchemaFailureClient()
    )
    provider = AgmarknetProvider(api_key="configured", max_retries=1)

    with caplog.at_level(logging.INFO), pytest.raises(MarketDataUnavailableError):
        await provider.fetch_prices(PriceQuery(commodity="Paddy"))

    assert "category=schema_error" in caplog.text


async def test_agmarknet_explicit_empty_records_is_successful_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class EmptyClient:
        async def get(self, url, **_request_options):
            request = httpx.Request("GET", url)
            return httpx.Response(200, request=request, json={"records": []})

    monkeypatch.setattr(
        "app.modules.market.provider.get_http_client", lambda: EmptyClient()
    )
    provider = AgmarknetProvider(api_key="configured", max_retries=1)

    assert await provider.fetch_prices(PriceQuery(commodity="NoSuchCrop")) == []


async def test_agmarknet_fetch_all_pages_until_short_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    offsets: list[int] = []

    class PagedClient:
        async def get(self, url, params=None, **_request_options):
            offset = int(params.get("offset", 0))
            offsets.append(offset)
            count = 2 if offset < 4 else 1  # pages of 2, then a short page
            request = httpx.Request("GET", url)
            records = [_record(market=f"M{offset + i}") for i in range(count)]
            return httpx.Response(200, request=request, json={"records": records})

    monkeypatch.setattr("app.modules.market.provider.get_http_client", lambda: PagedClient())
    provider = AgmarknetProvider(api_key="configured", max_retries=1)

    prices = await provider.fetch_all_prices(
        PriceQuery(state="Tamil Nadu", limit=2), max_pages=10
    )

    assert offsets == [0, 2, 4]
    assert [p.market for p in prices] == ["M0", "M1", "M2", "M3", "M4"]


async def test_agmarknet_uses_backup_resource_when_primary_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class PrimaryDownClient:
        async def get(self, url, **_request_options):
            if url.endswith("/primary"):
                raise httpx.ConnectTimeout("down")
            request = httpx.Request("GET", url)
            return httpx.Response(200, request=request, json={"records": [_record()]})

    monkeypatch.setattr(
        "app.modules.market.provider.get_http_client", lambda: PrimaryDownClient()
    )
    provider = AgmarknetProvider(
        api_key="configured", resource_id="primary", backup_resource_id="backup", max_retries=1
    )

    prices = await provider.fetch_prices(PriceQuery(commodity="Paddy"))

    assert [p.commodity for p in prices] == ["Paddy"]
