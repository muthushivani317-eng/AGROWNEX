"""AI dependency injection (docs/BACKEND_ARCHITECTURE.md → DI)."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.ai.service import AIService
from app.modules.auth.dependencies import CurrentUser
from app.modules.weather.service import WeatherService

__all__ = ["CurrentUser", "AIServiceDep"]


def get_ai_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AIService:
    # Weather is wired in so chats can include verified forecast context
    # (best-effort — the chat still works if weather is unavailable).
    return AIService(session, weather_service=WeatherService(session))


AIServiceDep = Annotated[AIService, Depends(get_ai_service)]
