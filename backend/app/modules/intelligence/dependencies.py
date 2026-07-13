"""Crop Intelligence dependency injection (docs/BACKEND_ARCHITECTURE.md → DI)."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.intelligence.service import IntelligenceService
from app.modules.weather.service import WeatherService

__all__ = ["CurrentUser", "IntelligenceServiceDep"]


def get_intelligence_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> IntelligenceService:
    # Weather is wired in so the aggregation can factor in the verified forecast
    # (best-effort — a refresh still works if weather is unavailable).
    return IntelligenceService(session, weather_service=WeatherService(session))


IntelligenceServiceDep = Annotated[
    IntelligenceService, Depends(get_intelligence_service)
]
