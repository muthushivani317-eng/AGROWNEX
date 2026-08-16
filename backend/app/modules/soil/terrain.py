"""Terrain evidence seam for Soil Scan.

No terrain values are synthesized. Deployments may supply a real provider behind
this protocol; the default remains explicitly unavailable.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class TerrainObservation:
    source: str
    observed_at: datetime
    reference: str
    quality: str
    slope_class: str | None = None
    geometry: dict | None = None


@dataclass(frozen=True)
class TerrainOutcome:
    state: str
    reason: str
    observations: tuple[TerrainObservation, ...] = ()


class TerrainProvider(Protocol):
    async def fetch(self, aoi_geojson: dict) -> TerrainOutcome: ...


class UnavailableTerrainProvider:
    async def fetch(self, aoi_geojson: dict) -> TerrainOutcome:
        return TerrainOutcome(
            state="unavailable",
            reason="terrain_provider_not_configured",
        )
