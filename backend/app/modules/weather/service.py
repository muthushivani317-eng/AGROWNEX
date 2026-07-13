"""Weather service — orchestrates fetch → parse → insights (docs/BACKEND_ARCHITECTURE).

API → Service → Repository. The service resolves coordinates, obtains a cached
raw forecast, parses it and derives deterministic insights.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.weather.cache import WeatherCache, weather_cache
from app.modules.weather.insights import build_insights
from app.modules.weather.parser import (
    parse_current,
    parse_daily,
    parse_hourly,
    parse_location,
)
from app.modules.weather.provider import ForecastProvider, OpenMeteoClient
from app.modules.weather.repository import WeatherRepository
from app.modules.weather.schemas import WeatherBundle


class WeatherService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        provider: ForecastProvider | None = None,
        cache: WeatherCache | None = None,
    ) -> None:
        self.repo = WeatherRepository(
            session, provider or OpenMeteoClient(), cache or weather_cache
        )

    async def get_by_farm(self, user: User, farm_id: uuid.UUID) -> WeatherBundle:
        latitude, longitude, name = await self.repo.resolve_coordinates(user, farm_id)
        return await self._build(latitude, longitude, name)

    async def get_by_coordinates(
        self, latitude: float, longitude: float
    ) -> WeatherBundle:
        return await self._build(latitude, longitude, None)

    async def _build(
        self, latitude: float, longitude: float, name: str | None
    ) -> WeatherBundle:
        raw = await self.repo.get_raw(latitude, longitude)
        current = parse_current(raw)
        hourly = parse_hourly(raw)
        daily = parse_daily(raw)
        return WeatherBundle(
            location=parse_location(raw, name),
            current=current,
            hourly=hourly,
            daily=daily,
            insights=build_insights(current, hourly, daily),
            fetched_at=datetime.now(UTC).isoformat(),
            source="open-meteo",
        )
