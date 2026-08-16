"""Weather service — orchestrates fetch → parse → insights (docs/BACKEND_ARCHITECTURE).

API → Service → Repository. The service resolves coordinates, obtains a cached
raw forecast, parses it and derives deterministic insights.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.action_verification.service import ActionVerificationService
from app.modules.auth.models import User
from app.modules.weather.action_source import weather_source_action
from app.modules.weather.cache import WeatherCache, weather_cache
from app.modules.weather.insights import build_insights
from app.modules.weather.mission import prioritize_mission
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
        self.session = session
        self.repo = WeatherRepository(
            session, provider or OpenMeteoClient(), cache or weather_cache
        )

    async def get_by_farm(self, user: User, farm_id: uuid.UUID) -> WeatherBundle:
        latitude, longitude, name, crop = await self.repo.resolve_farm_context(
            user, farm_id
        )
        bundle = await self._build(latitude, longitude, name, crop)
        source = weather_source_action(farm_id, bundle)
        if source is not None:
            await ActionVerificationService(self.session).register_source_action(
                user, farm_id, source
            )
        return bundle

    async def get_by_coordinates(
        self, latitude: float, longitude: float
    ) -> WeatherBundle:
        return await self._build(latitude, longitude, None, None)

    async def _build(
        self,
        latitude: float,
        longitude: float,
        name: str | None,
        crop: str | None,
    ) -> WeatherBundle:
        result = await self.repo.get_raw_with_provenance(latitude, longitude)
        raw = result.payload
        current = parse_current(raw)
        hourly = parse_hourly(raw)
        daily = parse_daily(raw)
        insights = build_insights(current, hourly, daily)
        return WeatherBundle(
            location=parse_location(raw, name),
            current=current,
            hourly=hourly,
            daily=daily,
            insights=insights,
            mission=prioritize_mission(insights, crop=crop),
            fetched_at=result.fetched_at,
            source="open-meteo",
            data_state=result.data_state,
        )
