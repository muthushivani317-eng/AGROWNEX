"""Weather cache layer (docs/API_CONTRACT.md → CACHING; BACKEND → Redis cache).

Caches parsed Open-Meteo responses, keyed by rounded coordinates, behind the
shared cache seam (``app.core.cache``). It is process-local in dev/tests and
Redis-backed in production (``CACHE_BACKEND=redis``) — no service change needed.
"""
from __future__ import annotations

from typing import Any

from app.core.cache import Cache, build_cache
from app.modules.weather.constants import CACHE_COORD_PRECISION, WEATHER_CACHE_TTL_SECONDS


class WeatherCache:
    def __init__(
        self,
        ttl_seconds: int = WEATHER_CACHE_TTL_SECONDS,
        *,
        backend: Cache | None = None,
    ) -> None:
        self.ttl = ttl_seconds
        self._backend = backend or build_cache(
            namespace="weather", ttl_seconds=ttl_seconds
        )

    @staticmethod
    def key(latitude: float, longitude: float) -> str:
        lat = round(latitude, CACHE_COORD_PRECISION)
        lng = round(longitude, CACHE_COORD_PRECISION)
        return f"{lat}:{lng}"

    def get(self, key: str) -> Any | None:
        return self._backend.get(key)

    def set(self, key: str, value: Any) -> None:
        self._backend.set(key, value)

    def clear(self) -> None:
        self._backend.clear()


# Process-wide singleton so cached forecasts are shared across requests.
weather_cache = WeatherCache()
