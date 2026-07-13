"""Unit tests for the deterministic Procurement Engine (pure, no I/O)."""
from __future__ import annotations

from datetime import date

from app.modules.produce.constants import HarvestWindow, ProduceUnit
from app.modules.produce.engine import (
    OfferFacts,
    PriceReference,
    classify_window,
    compute_insight,
    days_between,
    to_kilograms,
)

TODAY = date(2026, 7, 11)


def _ref(modal: float, unit: str = "quintal") -> PriceReference:
    return PriceReference(
        modal_price=modal,
        minimum_price=modal - 100,
        maximum_price=modal + 100,
        unit=unit,
        source="agmarknet",
        price_date=TODAY,
        market="Thanjavur",
        district="Thanjavur",
    )


# --------------------------------------------------------------------------- #
# days_between + classify_window
# --------------------------------------------------------------------------- #
def test_days_between_positive_and_negative() -> None:
    assert days_between(date(2026, 7, 18), TODAY) == 7
    assert days_between(date(2026, 7, 11), TODAY) == 0
    assert days_between(date(2026, 7, 1), TODAY) == -10


def test_classify_window_buckets() -> None:
    assert classify_window(-1) == HarvestWindow.OVERDUE.value
    assert classify_window(0) == HarvestWindow.THIS_WEEK.value
    assert classify_window(7) == HarvestWindow.THIS_WEEK.value
    assert classify_window(8) == HarvestWindow.THIS_MONTH.value
    assert classify_window(30) == HarvestWindow.THIS_MONTH.value
    assert classify_window(31) == HarvestWindow.LATER.value


# --------------------------------------------------------------------------- #
# to_kilograms
# --------------------------------------------------------------------------- #
def test_to_kilograms_conversions() -> None:
    assert to_kilograms(2, ProduceUnit.QUINTAL.value) == 200.0
    assert to_kilograms(1.5, ProduceUnit.TONNE.value) == 1500.0
    assert to_kilograms(50, ProduceUnit.KG.value) == 50.0


def test_to_kilograms_non_standard_unit_is_none() -> None:
    assert to_kilograms(10, ProduceUnit.BAG.value) is None


# --------------------------------------------------------------------------- #
# compute_insight
# --------------------------------------------------------------------------- #
def test_insight_without_price_has_no_market_value() -> None:
    offer = OfferFacts(quantity=10, unit="quintal", expected_harvest_date=date(2026, 7, 20))
    insight = compute_insight(offer, None, today=TODAY)
    assert insight.days_to_harvest == 9
    assert insight.harvest_window == HarvestWindow.THIS_MONTH.value
    assert insight.quantity_kg == 1000.0
    assert insight.estimated_market_value is None  # never fabricated
    assert insight.estimated_asking_value is None
    assert insight.price_reference is None


def test_insight_market_value_uses_verified_price_same_unit() -> None:
    # 20 quintal at ₹2,000/quintal → ₹40,000.
    offer = OfferFacts(quantity=20, unit="quintal", expected_harvest_date=date(2026, 7, 15))
    insight = compute_insight(offer, _ref(2000), today=TODAY)
    assert insight.estimated_market_value == 40000.0
    assert insight.price_reference is not None


def test_insight_market_value_converts_units() -> None:
    # 2 tonne (= 20 quintal) at ₹2,000/quintal → ₹40,000.
    offer = OfferFacts(quantity=2, unit="tonne", expected_harvest_date=date(2026, 7, 15))
    insight = compute_insight(offer, _ref(2000, unit="quintal"), today=TODAY)
    assert insight.estimated_market_value == 40000.0


def test_insight_market_value_none_for_non_convertible_unit() -> None:
    offer = OfferFacts(quantity=5, unit="bag", expected_harvest_date=date(2026, 7, 15))
    insight = compute_insight(offer, _ref(2000), today=TODAY)
    assert insight.quantity_kg is None
    assert insight.estimated_market_value is None


def test_insight_asking_value_from_farmer_price() -> None:
    offer = OfferFacts(
        quantity=10, unit="quintal", expected_harvest_date=date(2026, 7, 15),
        asking_price=2200,
    )
    insight = compute_insight(offer, None, today=TODAY)
    assert insight.estimated_asking_value == 22000.0


def test_insight_overdue_harvest() -> None:
    offer = OfferFacts(quantity=1, unit="quintal", expected_harvest_date=date(2026, 7, 1))
    insight = compute_insight(offer, None, today=TODAY)
    assert insight.days_to_harvest == -10
    assert insight.harvest_window == HarvestWindow.OVERDUE.value
