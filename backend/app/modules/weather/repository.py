"""Weather data-access layer (docs/BACKEND_ARCHITECTURE.md → Repository Pattern).

Weather has no table of its own; its "data" lives in an external service
(Open-Meteo) plus a cache, and the farm's coordinates come from the farms table.
This repository is the single boundary for both — the service never calls the
provider/cache or the farm store directly.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.modules.auth.models import User
from app.modules.farms.exceptions import FarmNotFoundError
from app.modules.farms.repositories import FarmRepository
from app.modules.weather.cache import WeatherCache
from app.modules.weather.exceptions import FarmLocationMissingError
from app.modules.weather.provider import ForecastProvider


@dataclass(frozen=True)
class WeatherRawResult:
    payload: dict[str, Any]
    fetched_at: str
    data_state: str


class WeatherRepository:
    def __init__(
        self, session, provider: ForecastProvider, cache: WeatherCache
    ) -> None:
        self.farms = FarmRepository(session)
        self.provider = provider
        self.cache = cache

    async def resolve_farm_context(
        self, user: User, farm_id: uuid.UUID
    ) -> tuple[float, float, str | None, str | None]:
        farm = await self.farms.get_for_user(farm_id, user.id)
        if farm is None:
            raise FarmNotFoundError()
        location = farm.location
        if location is None or location.latitude is None or location.longitude is None:
            raise FarmLocationMissingError()
        return location.latitude, location.longitude, farm.name, farm.crop

    async def get_raw_with_provenance(
        self, latitude: float, longitude: float
    ) -> WeatherRawResult:
        key = self.cache.key(latitude, longitude)
        cached = self.cache.get(key)
        if cached is not None:
            if (
                isinstance(cached, dict)
                and cached.get("_agrowai_weather_cache_version") == 1
                and isinstance(cached.get("payload"), dict)
                and isinstance(cached.get("fetched_at"), str)
            ):
                return WeatherRawResult(
                    payload=cached["payload"],
                    fetched_at=cached["fetched_at"],
                    data_state="cached",
                )
            # A legacy cache value has no trustworthy observation timestamp.
            # Ignore it and refresh instead of presenting it as live/current.
        raw = await self.provider.fetch(latitude, longitude)
        fetched_at = datetime.now(UTC).isoformat()
        self.cache.set(
            key,
            {
                "_agrowai_weather_cache_version": 1,
                "payload": raw,
                "fetched_at": fetched_at,
            },
        )
        return WeatherRawResult(
            payload=raw,
            fetched_at=fetched_at,
            data_state="live",
        )

    async def get_raw(self, latitude: float, longitude: float) -> dict[str, Any]:
        """Compatibility accessor for callers that only need the raw forecast."""
        return (await self.get_raw_with_provenance(latitude, longitude)).payload
