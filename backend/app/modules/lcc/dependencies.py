from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.lcc.service import LccService


def get_lcc_service(session: Annotated[AsyncSession, Depends(get_session)]) -> LccService:
    return LccService(session)


LccServiceDep = Annotated[LccService, Depends(get_lcc_service)]
