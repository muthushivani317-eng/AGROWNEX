"""Unit tests for market providers (no network — parsing + mock + selection)."""
from __future__ import annotations

from datetime import date

import pytest
from app.modules.market.constants import PriceUnit
from app.modules.market.provider import (
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
    # Missing credentials must never synthesize farmer-facing prices.
    provider = get_default_provider()
    assert provider.source == "unavailable"
