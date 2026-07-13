"""Farm Memory dependency injection (docs/BACKEND_ARCHITECTURE.md → DI)."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.memory.service import MemoryService
from app.modules.weather.service import WeatherService

__all__ = ["CurrentUser", "MemoryServiceDep"]


def get_memory_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MemoryService:
    # Weather is wired in so a rebuild can remember notable verified weather events
    # (best-effort — a rebuild still works if weather is unavailable).
    return MemoryService(session, weather_service=WeatherService(session))


MemoryServiceDep = Annotated[MemoryService, Depends(get_memory_service)]
