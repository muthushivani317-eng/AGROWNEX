"""Weather dependency injection (docs/BACKEND_ARCHITECTURE.md → DI)."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.weather.service import WeatherService

__all__ = ["CurrentUser", "WeatherServiceDep"]


def get_weather_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> WeatherService:
    return WeatherService(session)


WeatherServiceDep = Annotated[WeatherService, Depends(get_weather_service)]
