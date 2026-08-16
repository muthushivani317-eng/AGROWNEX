from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.produce.harvest_readiness_service import HarvestReadinessService


def get_harvest_readiness_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> HarvestReadinessService:
    return HarvestReadinessService(session)


HarvestReadinessServiceDep = Annotated[
    HarvestReadinessService, Depends(get_harvest_readiness_service)
]

__all__ = ["CurrentUser", "HarvestReadinessServiceDep"]
