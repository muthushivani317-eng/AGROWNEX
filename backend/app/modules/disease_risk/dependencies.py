from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session

from .service import DiseaseRiskService


def get_disease_risk_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DiseaseRiskService:
    return DiseaseRiskService(session)


DiseaseRiskServiceDep = Annotated[DiseaseRiskService, Depends(get_disease_risk_service)]
