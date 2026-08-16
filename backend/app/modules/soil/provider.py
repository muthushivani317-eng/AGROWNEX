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
from datetime import date
from typing import Protocol

from app.core.logging import get_logger

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


@dataclass(frozen=True)
class RemoteSoilEstimate:
    indicator: str
    value: float
    unit: str
    provider: str
    model_version: str
    scene_id: str
    aoi_hash: str
    capture_date: date
    resolution_m: float
    coverage_pct: float
    uncertainty_low: float | None
    uncertainty_high: float | None


@dataclass(frozen=True)
class RemoteSoilOutcome:
    estimates: tuple[RemoteSoilEstimate, ...] = ()
    status: str = "insufficient_data"
    reason: str = "provider_not_configured"


class SoilProvider(Protocol):
    """Supplies soil data from an external source. The external seam."""

    name: str

    async def fetch_location_soil(
        self, latitude: float, longitude: float
    ) -> ProviderSoilData | None: ...

    async def parse_report(self, report_url: str, mime_type: str | None) -> ParsedReport | None: ...

    async def fetch_remote_estimates(self, aoi: dict) -> RemoteSoilOutcome: ...


class MockSoilProvider:
    """No external soil source in V1 — returns nothing, fabricates nothing."""

    name = "mock"

    async def fetch_location_soil(
        self, latitude: float, longitude: float
    ) -> ProviderSoilData | None:
        # No verified location soil dataset wired in → no data (never invented).
        logger.info("no location soil dataset configured (%.4f, %.4f)", latitude, longitude)
        return None

    async def parse_report(self, report_url: str, mime_type: str | None) -> ParsedReport | None:
        # No OCR / lab API wired in → the farmer supplies the values (never invented).
        return None

    async def fetch_remote_estimates(self, aoi: dict) -> RemoteSoilOutcome:
        return RemoteSoilOutcome()


class UnavailableSoilProvider:
    """Production-safe null provider; it never returns sample soil values."""

    name = "unavailable"

    async def fetch_location_soil(
        self, latitude: float, longitude: float
    ) -> ProviderSoilData | None:
        return None

    async def parse_report(self, report_url: str, mime_type: str | None) -> ParsedReport | None:
        return None

    async def fetch_remote_estimates(self, aoi: dict) -> RemoteSoilOutcome:
        return RemoteSoilOutcome(
            status="remote_estimation_unavailable",
            reason="provider_not_configured",
        )


def get_default_provider() -> SoilProvider:
    """Select an explicit development mock or fail closed without a real adapter."""
    import os

    configured = os.getenv("SOIL_PROVIDER", "").lower()
    environment = os.getenv("ENVIRONMENT", "development").lower()
    if configured == "mock" and environment in {"development", "test"}:
        logger.info("soil provider: explicit development mock")
        return MockSoilProvider()
    if configured:
        logger.warning("soil provider unavailable: configured adapter is not installed")
    else:
        logger.info("soil provider unavailable: no real adapter configured")
    return UnavailableSoilProvider()
