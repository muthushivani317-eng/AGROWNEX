from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.auth.dependencies import CurrentUser

from .service import OrganicLogbookService


def get_service(session: Annotated[AsyncSession, Depends(get_session)]):
    return OrganicLogbookService(session)


OrganicLogbookServiceDep = Annotated[OrganicLogbookService, Depends(get_service)]
__all__ = ["CurrentUser", "OrganicLogbookServiceDep"]
