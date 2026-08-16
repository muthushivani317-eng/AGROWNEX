"""Nutrient dependency injection (docs/BACKEND_ARCHITECTURE.md → DI)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.nutrient.service import NutrientService
from app.modules.weather.service import WeatherService

__all__ = ["CurrentUser", "NutrientServiceDep"]


def get_nutrient_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> NutrientService:
    # Weather is wired in so each analysis can corroborate with (and store) a
    # verified weather snapshot — best-effort; analysis still works without it.
    return NutrientService(session, weather_service=WeatherService(session))


NutrientServiceDep = Annotated[NutrientService, Depends(get_nutrient_service)]
