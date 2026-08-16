"""Calendar dependency injection (docs/BACKEND_ARCHITECTURE.md → DI)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.calendar.service import CalendarService
from app.modules.weather.service import WeatherService

__all__ = ["CurrentUser", "CalendarServiceDep"]


def get_calendar_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CalendarService:
    # Weather is wired in so read endpoints can add advisories, reusing the
    # Weather module (best-effort — the calendar works without weather too).
    return CalendarService(session, weather_service=WeatherService(session))


CalendarServiceDep = Annotated[CalendarService, Depends(get_calendar_service)]
