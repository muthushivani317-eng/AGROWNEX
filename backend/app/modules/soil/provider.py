"""Soil data providers (docs: provider abstraction; future lab/gov/satellite/OCR).

``SoilProvider`` is the seam that supplies soil data *from outside the app* — a
government soil dataset, an accredited laboratory API, a satellite soil layer, or
Gemini OCR of an uploaded Soil Health Card (docs/AI_DECISION_MATRIX → Soil Report
PDF → Gemini). V1 ships a ``MockSoilProvider`` that returns **nothing**: it never
fabricates a soil value (docs/PRODUCT_RULES.md). Farmer-entered values are the only
source of truth in V1. Future providers implement the same Protocol and are
selected in ``get_default_provider`` with no change to the rest of the module.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.core.logging import get_logger
from app.modules.soil.constants import SOIL_PROVIDER

logger = get_logger("soil.provider")


@dataclass(frozen=True)
class ProviderSoilData:
    """Soil values from an external dataset (future). Any field may be ``None``."""

    ph: float | None = None
    organic_carbon: float | None = None
    nitrogen: float | None = None
    phosphorus: float | None = None
    potassium: float | None = None
    ec_salinity: float | None = None
    water_holding_capacity: float | None = None
    drainage: str | None = None
    soil_type: str | None = None
    micronutrients: dict[str, float] = field(default_factory=dict)
    source: str | None = None
    confidence: int | None = None


@dataclass(frozen=True)
class ParsedReport:
    """The result of parsing an uploaded report (future Gemini OCR / lab API)."""

    values: ProviderSoilData
    lab_name: str | None = None
    test_date: str | None = None


class SoilProvider(Protocol):
    """Supplies soil data from an external source. The external seam."""

    name: str

    async def fetch_location_soil(
        self, latitude: float, longitude: float
    ) -> ProviderSoilData | None: ...

    async def parse_report(
        self, report_url: str, mime_type: str | None
    ) -> ParsedReport | None: ...


class MockSoilProvider:
    """No external soil source in V1 — returns nothing, fabricates nothing."""

    name = "mock"

    async def fetch_location_soil(
        self, latitude: float, longitude: float
    ) -> ProviderSoilData | None:
        # No verified location soil dataset wired in → no data (never invented).
        logger.info("no location soil dataset configured (%.4f, %.4f)", latitude, longitude)
        return None

    async def parse_report(
        self, report_url: str, mime_type: str | None
    ) -> ParsedReport | None:
        # No OCR / lab API wired in → the farmer supplies the values (never invented).
        return None


def get_default_provider() -> SoilProvider:
    """Select the configured provider (mock until a real source is wired in)."""
    if SOIL_PROVIDER:
        logger.info(
            "soil provider '%s' requested but not wired; using mock", SOIL_PROVIDER
        )
    return MockSoilProvider()
