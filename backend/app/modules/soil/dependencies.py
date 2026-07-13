"""Soil Intelligence dependency injection (docs/BACKEND_ARCHITECTURE.md → DI)."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.soil.service import SoilService

__all__ = ["CurrentUser", "SoilServiceDep"]


def get_soil_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SoilService:
    return SoilService(session)


SoilServiceDep = Annotated[SoilService, Depends(get_soil_service)]
