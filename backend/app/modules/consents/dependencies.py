from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session

from .service import ConsentService


def get_consent_service(session: Annotated[AsyncSession, Depends(get_session)]) -> ConsentService:
    return ConsentService(session)


ConsentServiceDep = Annotated[ConsentService, Depends(get_consent_service)]
