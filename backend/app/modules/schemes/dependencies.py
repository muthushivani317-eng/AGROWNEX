"""Scheme dependency injection (docs/BACKEND_ARCHITECTURE.md → DI)."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.schemes.service import SchemeService

__all__ = ["CurrentUser", "SchemeServiceDep"]


def get_scheme_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SchemeService:
    return SchemeService(session)


SchemeServiceDep = Annotated[SchemeService, Depends(get_scheme_service)]
