"""Growth dependency injection (docs/BACKEND_ARCHITECTURE.md → DI)."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.growth.service import GrowthService
from app.modules.weather.service import WeatherService

__all__ = ["CurrentUser", "GrowthServiceDep"]


def get_growth_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GrowthService:
    # Weather is wired in so each upload can store a verified weather snapshot
    # (best-effort — analysis still works if weather is unavailable).
    return GrowthService(session, weather_service=WeatherService(session))


GrowthServiceDep = Annotated[GrowthService, Depends(get_growth_service)]
