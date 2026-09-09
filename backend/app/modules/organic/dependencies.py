from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.organic.service import OrganicService


def get_organic_service(session: Annotated[AsyncSession, Depends(get_session)]) -> OrganicService:
    return OrganicService(session)


OrganicServiceDep = Annotated[OrganicService, Depends(get_organic_service)]
