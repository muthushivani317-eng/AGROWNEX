"""Procurement Engine (docs: Repository → Service → Procurement Engine → Provider).

Pure, deterministic and fully unit-tested. Given a harvest offer and an *optional*
verified market-price reference it computes procurement intelligence: how soon the
harvest is due, a normalized quantity, and indicative values. It never fabricates
a market price or a buyer — a market value is produced only when a verified price
reference is supplied (docs/PRODUCT_RULES.md). No I/O, no side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.modules.produce.constants import (
    UNIT_KG,
    WINDOW_MONTH_DAYS,
    WINDOW_WEEK_DAYS,
    HarvestWindow,
)


@dataclass(frozen=True)
class PriceReference:
    """A verified market-price snapshot (from the Market module). Never fabricated."""

    modal_price: float
    minimum_price: float
    maximum_price: float
    unit: str
    source: str
    price_date: date
    market: str | None = None
    district: str | None = None


@dataclass(frozen=True)
class OfferFacts:
    """The subset of an offer the engine reasons about (pure inputs)."""

    quantity: float
    unit: str
    expected_harvest_date: date
    asking_price: float | None = None


@dataclass(frozen=True)
class ProcurementInsight:
    """Deterministic, explainable output of the engine."""

    days_to_harvest: int
    harvest_window: str
    quantity_kg: float | None
    estimated_market_value: float | None
    estimated_asking_value: float | None
    price_reference: PriceReference | None


def days_between(target: date, today: date) -> int:
    """Whole days from ``today`` to ``target`` (negative if in the past)."""
    return (target - today).days


def classify_window(days_to_harvest: int) -> str:
    """Bucket a harvest by how soon it is due (pure)."""
    if days_to_harvest < 0:
        return HarvestWindow.OVERDUE.value
    if days_to_harvest <= WINDOW_WEEK_DAYS:
        return HarvestWindow.THIS_WEEK.value
    if days_to_harvest <= WINDOW_MONTH_DAYS:
        return HarvestWindow.THIS_MONTH.value
    return HarvestWindow.LATER.value


def to_kilograms(quantity: float, unit: str) -> float | None:
    """Convert a quantity to kilograms, or ``None`` for non-standard units (bag)."""
    factor = UNIT_KG.get(unit)
    if factor is None:
        return None
    return quantity * factor


def _value_from_price(quantity_kg: float | None, price_per_unit: float, unit: str) -> float | None:
    """Total value = quantity (in the price's unit) × price. ``None`` if not convertible."""
    unit_kg = UNIT_KG.get(unit)
    if quantity_kg is None or unit_kg is None or unit_kg <= 0:
        return None
    quantity_in_price_unit = quantity_kg / unit_kg
    return round(quantity_in_price_unit * price_per_unit, 2)


def compute_insight(
    offer: OfferFacts,
    price: PriceReference | None,
    *,
    today: date,
) -> ProcurementInsight:
    """Enrich an offer with procurement intelligence (pure)."""
    days = days_between(offer.expected_harvest_date, today)
    quantity_kg = to_kilograms(offer.quantity, offer.unit)

    # Market value only when a verified price reference is supplied.
    estimated_market_value = (
        _value_from_price(quantity_kg, price.modal_price, price.unit) if price is not None else None
    )

    # The farmer's own asking price is per the offer's unit (not fabricated data).
    estimated_asking_value = (
        round(offer.quantity * offer.asking_price, 2) if offer.asking_price is not None else None
    )

    return ProcurementInsight(
        days_to_harvest=days,
        harvest_window=classify_window(days),
        quantity_kg=quantity_kg,
        estimated_market_value=estimated_market_value,
        estimated_asking_value=estimated_asking_value,
        price_reference=price,
    )
