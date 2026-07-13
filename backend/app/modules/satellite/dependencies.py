"""Satellite Intelligence dependency injection (docs/BACKEND_ARCHITECTURE.md → DI)."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.satellite.service import SatelliteService

__all__ = ["CurrentUser", "SatelliteServiceDep"]


def get_satellite_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SatelliteService:
    return SatelliteService(session)


SatelliteServiceDep = Annotated[SatelliteService, Depends(get_satellite_service)]
