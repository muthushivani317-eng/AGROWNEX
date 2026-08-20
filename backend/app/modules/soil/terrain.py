"""Terrain evidence for transparent erosion and drainage screening."""

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

import httpx

from app.modules.farms.geo import InvalidPolygonError, centroid, extract_ring, validate_ring


@dataclass(frozen=True)
class TerrainObservation:
    source: str
    observed_at: datetime
    reference: str
    quality: str
    slope_class: str | None = None
    mean_slope_degrees: float | None = None
    elevation_range_m: float | None = None
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


class OpenMeteoElevationProvider:
    """Sample real mapped elevations and derive a coarse field-scale slope.

    This is screening evidence, not a surveyed contour map. Five points are
    used (centroid plus up to four boundary vertices), and the steepest
    centroid-to-vertex grade is retained so small fields are not flattened by
    averaging opposite slopes.
    """

    URL = "https://api.open-meteo.com/v1/elevation"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def fetch(self, aoi_geojson: dict) -> TerrainOutcome:
        try:
            ring = validate_ring(extract_ring(aoi_geojson))
            center_lat, center_lon = centroid(ring)
        except (InvalidPolygonError, TypeError, ValueError):
            return TerrainOutcome("unavailable", "invalid_aoi")
        points = [(center_lon, center_lat), *ring[:4]]
        client = self._client
        owns_client = client is None
        if owns_client:
            client = httpx.AsyncClient(timeout=12.0)
        try:
            response = await client.get(
                self.URL,
                params={
                    "latitude": ",".join(str(point[1]) for point in points),
                    "longitude": ",".join(str(point[0]) for point in points),
                },
            )
            response.raise_for_status()
            elevations = response.json().get("elevation")
        except (httpx.HTTPError, ValueError, AttributeError):
            return TerrainOutcome("unavailable", "terrain_provider_error")
        finally:
            if owns_client:
                await client.aclose()
        if not isinstance(elevations, list) or len(elevations) != len(points):
            return TerrainOutcome("unavailable", "terrain_no_data")
        if any(
            not isinstance(value, int | float) or isinstance(value, bool)
            for value in elevations
        ):
            return TerrainOutcome("unavailable", "terrain_no_data")
        center_elevation = float(elevations[0])
        slopes: list[float] = []
        for point, elevation in zip(points[1:], elevations[1:], strict=True):
            distance = self._distance_m(points[0], point)
            if distance >= 1:
                grade = abs(float(elevation) - center_elevation) / distance
                slopes.append(math.degrees(math.atan(grade)))
        if not slopes:
            return TerrainOutcome("unavailable", "terrain_no_data")
        mean_slope = round(max(slopes), 2)
        if mean_slope < 2:
            slope_class = "flat"
        elif mean_slope < 5:
            slope_class = "gentle"
        elif mean_slope < 10:
            slope_class = "moderate"
        else:
            slope_class = "steep"
        observed_at = datetime.now(UTC)
        return TerrainOutcome(
            "available",
            "none",
            (
                TerrainObservation(
                    source="open_meteo_elevation",
                    observed_at=observed_at,
                    reference=f"elevation:{center_lat:.5f},{center_lon:.5f}",
                    quality="screening",
                    slope_class=slope_class,
                    mean_slope_degrees=mean_slope,
                    elevation_range_m=round(max(elevations) - min(elevations), 1),
                    geometry=aoi_geojson,
                ),
            ),
        )

    @staticmethod
    def _distance_m(a: tuple[float, float], b: tuple[float, float]) -> float:
        lon1, lat1 = map(math.radians, a)
        lon2, lat2 = map(math.radians, b)
        dlat, dlon = lat2 - lat1, lon2 - lon1
        value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        return 6_371_000 * 2 * math.asin(math.sqrt(value))
