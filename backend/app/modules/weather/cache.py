"""Weather cache layer (docs/API_CONTRACT.md → CACHING; BACKEND → Redis cache).

An in-process TTL cache for parsed Open-Meteo responses, keyed by rounded
coordinates. The interface is deliberately small so a Redis-backed implementation
can replace it in production without touching the service.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from app.modules.weather.constants import CACHE_COORD_PRECISION, WEATHER_CACHE_TTL_SECONDS


@dataclass
class _Entry:
    value: Any
    expires_at: float


class WeatherCache:
    def __init__(self, ttl_seconds: int = WEATHER_CACHE_TTL_SECONDS) -> None:
        self.ttl = ttl_seconds
        self._store: dict[str, _Entry] = {}

    @staticmethod
    def key(latitude: float, longitude: float) -> str:
        lat = round(latitude, CACHE_COORD_PRECISION)
        lng = round(longitude, CACHE_COORD_PRECISION)
        return f"{lat}:{lng}"

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.expires_at <= time.monotonic():
            self._store.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = _Entry(value=value, expires_at=time.monotonic() + self.ttl)

    def clear(self) -> None:
        self._store.clear()


# Process-wide singleton so cached forecasts are shared across requests.
weather_cache = WeatherCache()
