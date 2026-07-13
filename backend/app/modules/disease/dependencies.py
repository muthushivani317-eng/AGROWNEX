"""Disease dependency injection (docs/BACKEND_ARCHITECTURE.md → DI)."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.disease.service import DiseaseService
from app.modules.weather.service import WeatherService

__all__ = ["CurrentUser", "DiseaseServiceDep"]


def get_disease_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DiseaseService:
    # Weather is wired in so each report can store a verified weather snapshot
    # (best-effort — analysis still works if weather is unavailable).
    return DiseaseService(session, weather_service=WeatherService(session))


DiseaseServiceDep = Annotated[DiseaseService, Depends(get_disease_service)]
