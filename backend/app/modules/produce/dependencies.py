"""Produce dependency injection (docs/BACKEND_ARCHITECTURE.md → DI)."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.produce.service import ProduceService

__all__ = ["CurrentUser", "ProduceServiceDep"]


def get_produce_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProduceService:
    return ProduceService(session)


ProduceServiceDep = Annotated[ProduceService, Depends(get_produce_service)]
