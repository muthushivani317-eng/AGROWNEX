from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.inputs_marketplace.service import InputsMarketplaceService


def get_inputs_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> InputsMarketplaceService:
    return InputsMarketplaceService(session)


InputsServiceDep = Annotated[InputsMarketplaceService, Depends(get_inputs_service)]
