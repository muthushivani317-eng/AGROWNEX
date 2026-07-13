"""Weather data-access layer (docs/BACKEND_ARCHITECTURE.md → Repository Pattern).

Weather has no table of its own; its "data" lives in an external service
(Open-Meteo) plus a cache, and the farm's coordinates come from the farms table.
This repository is the single boundary for both — the service never calls the
provider/cache or the farm store directly.
"""
from __future__ import annotations

import uuid
from typing import Any

from app.modules.auth.models import User
from app.modules.farms.exceptions import FarmNotFoundError
from app.modules.farms.repositories import FarmRepository
from app.modules.weather.cache import WeatherCache
from app.modules.weather.exceptions import FarmLocationMissingError
from app.modules.weather.provider import ForecastProvider


class WeatherRepository:
    def __init__(
        self, session, provider: ForecastProvider, cache: WeatherCache
    ) -> None:
        self.farms = FarmRepository(session)
        self.provider = provider
        self.cache = cache

    async def resolve_coordinates(
        self, user: User, farm_id: uuid.UUID
    ) -> tuple[float, float, str | None]:
        farm = await self.farms.get_for_user(farm_id, user.id)
        if farm is None:
            raise FarmNotFoundError()
        location = farm.location
        if location is None or location.latitude is None or location.longitude is None:
            raise FarmLocationMissingError()
        return location.latitude, location.longitude, farm.name

    async def get_raw(self, latitude: float, longitude: float) -> dict[str, Any]:
        key = self.cache.key(latitude, longitude)
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        raw = await self.provider.fetch(latitude, longitude)
        self.cache.set(key, raw)
        return raw
