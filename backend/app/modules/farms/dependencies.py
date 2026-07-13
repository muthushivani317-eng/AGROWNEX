"""Farm dependency injection (docs/BACKEND_ARCHITECTURE.md → Dependency Injection).

Reuses the authenticated-user dependency from the auth module.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.farms.service import FarmService

__all__ = ["CurrentUser", "FarmServiceDep"]


def get_farm_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FarmService:
    return FarmService(session)


FarmServiceDep = Annotated[FarmService, Depends(get_farm_service)]
