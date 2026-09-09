from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.weather.service import WeatherService

from .service import OrganicAdvisoryService


def get_service(session: Annotated[AsyncSession, Depends(get_session)]):
    return OrganicAdvisoryService(session, weather=WeatherService(session))


OrganicAdvisoryServiceDep = Annotated[OrganicAdvisoryService, Depends(get_service)]
