"""Satellite providers (docs: provider abstraction; FREE Sentinel-2 first).

``SatelliteProvider`` is the seam that supplies scenes from an imagery source. V1
targets **free Sentinel-2** (Copernicus Data Space). Without credentials the
``SentinelProvider`` returns an honest *unavailable* outcome — it never invents a
scene (docs/PRODUCT_RULES.md). A ``MockSatelliteProvider`` produces *deterministic
sample* indices (clearly flagged ``is_sample`` / ``provider="mock"``, and with **no**
fabricated imagery) for development and tests. Future providers (Sentinel Hub,
Copernicus Data Space API, Planet, Maxar, Earth Engine, Azure Planetary Computer)
implement the same Protocol and are selected in ``get_default_provider`` with no
change to the service, API or frontend.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Protocol

from app.core.logging import get_logger
from app.modules.satellite.constants import (
    SATELLITE_PROVIDER,
    SatelliteProviderName,
    UnavailableReason,
)
from app.modules.satellite.engine import BandReflectance, IndexValues

logger = get_logger("satellite.provider")


@dataclass(frozen=True)
class ProviderScene:
    """A scene returned by a provider. Bands (or precomputed indices) + metadata."""

    capture_date: date
    provider: str
    cloud_cover: float
    resolution_m: float
    bands: BandReflectance | None = None
    indices: IndexValues | None = None
    # index_name → (mean, min, max, std) for field-variation detection.
    index_stats: dict[str, tuple[float, float, float, float]] = field(default_factory=dict)
    images: dict[str, str] = field(default_factory=dict)  # band → image URL
    thumbnail_url: str | None = None
    is_sample: bool = False
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class FetchOutcome:
    """A scene, or an honest reason it is unavailable."""

    scene: ProviderScene | None
    reason: str = UnavailableReason.NONE.value


class SatelliteProvider(Protocol):
    name: str

    async def fetch_scene(self, polygon: dict, *, capture_before: date) -> FetchOutcome: ...


def _polygon_seed(polygon: dict) -> int:
    """A stable integer seed from a polygon's coordinates (deterministic mock)."""
    raw = str(polygon.get("coordinates", polygon)).encode("utf-8")
    return int(hashlib.sha256(raw).hexdigest(), 16)


class SentinelProvider:
    """Free Sentinel-2 (Copernicus Data Space). Honest "not available" until wired.

    A real implementation queries the Copernicus STAC/OData API for the most recent
    low-cloud scene over the polygon and reads band statistics. Without credentials
    it never fabricates a scene — it reports the imagery as unavailable.
    """

    name = SatelliteProviderName.SENTINEL.value

    def __init__(self, *, configured: bool = False) -> None:
        self._configured = configured

    async def fetch_scene(self, polygon: dict, *, capture_before: date) -> FetchOutcome:
        if not self._configured:
            logger.info("sentinel provider not configured → imagery unavailable")
            return FetchOutcome(scene=None, reason=UnavailableReason.PROVIDER_ERROR.value)
        # Future: real Copernicus query. Until then, be honest.
        return FetchOutcome(scene=None, reason=UnavailableReason.NO_IMAGERY.value)


class MockSatelliteProvider:
    """Deterministic *sample* provider (dev/tests). Flags every scene ``is_sample``
    and supplies **no** fabricated imagery — only reproducible sample indices."""

    name = SatelliteProviderName.MOCK.value

    async def fetch_scene(self, polygon: dict, *, capture_before: date) -> FetchOutcome:
        seed = _polygon_seed(polygon)
        # Deterministic, plausible band reflectances (0-1).
        ndvi_target = 0.35 + (seed % 40) / 100.0          # 0.35 – 0.74
        ndmi_target = 0.10 + (seed % 30) / 100.0          # 0.10 – 0.39
        nir = 0.45
        red = round(nir * (1 - ndvi_target) / (1 + ndvi_target), 4)
        red_edge = round(red + 0.6 * (nir - red), 4)
        swir = round(nir * (1 - ndmi_target) / (1 + ndmi_target), 4)
        bands = BandReflectance(red=red, nir=nir, red_edge=red_edge, swir=swir, blue=0.06)
        cloud_cover = float(seed % 20)  # 0 – 19 % (usable sample scene)
        capture_date = capture_before - timedelta(days=1 + (seed % 5))
        return FetchOutcome(
            scene=ProviderScene(
                capture_date=capture_date,
                provider=self.name,
                cloud_cover=cloud_cover,
                resolution_m=10.0,
                bands=bands,
                index_stats={"ndvi": (ndvi_target, ndvi_target - 0.05, ndvi_target + 0.05, 0.05)},
                images={},  # never fabricate imagery — sample mode is numeric only
                is_sample=True,
                metadata={"note": "sample data (development only)"},
            )
        )


def get_default_provider() -> SatelliteProvider:
    """Select the configured provider. Defaults to the honest Sentinel seam; set
    SATELLITE_PROVIDER=mock to use deterministic sample data in development."""
    if SATELLITE_PROVIDER == SatelliteProviderName.MOCK.value:
        logger.info("satellite provider: mock (sample data)")
        return MockSatelliteProvider()
    logger.info("satellite provider: sentinel (free Sentinel-2 seam)")
    return SentinelProvider()
