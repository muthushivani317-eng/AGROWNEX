"""Market dependency injection (docs/BACKEND_ARCHITECTURE.md → DI)."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.market.service import MarketService

__all__ = ["CurrentUser", "MarketServiceDep"]


def get_market_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MarketService:
    return MarketService(session)


MarketServiceDep = Annotated[MarketService, Depends(get_market_service)]
