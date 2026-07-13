"""Expert Connect dependency injection (docs/BACKEND_ARCHITECTURE.md → DI)."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.experts.service import ExpertService

__all__ = ["CurrentUser", "ExpertServiceDep"]


def get_expert_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ExpertService:
    return ExpertService(session)


ExpertServiceDep = Annotated[ExpertService, Depends(get_expert_service)]
