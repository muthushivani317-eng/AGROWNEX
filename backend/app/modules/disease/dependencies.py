"""Disease dependency injection (docs/BACKEND_ARCHITECTURE.md → DI)."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.disease.service import DiseaseService

__all__ = ["CurrentUser", "DiseaseServiceDep"]


def get_disease_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DiseaseService:
    return DiseaseService(session)


DiseaseServiceDep = Annotated[DiseaseService, Depends(get_disease_service)]
