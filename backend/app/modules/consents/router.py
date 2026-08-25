from typing import Literal

from fastapi import APIRouter, HTTPException, status

from app.modules.auth.dependencies import CurrentUser
from app.schemas.response import SuccessResponse, success

from .dependencies import ConsentServiceDep
from .schemas import ConsentDecisionRequest, ConsentOverviewOut, ConsentStateOut, CoreProcessingOut
from .service import ConsentWriteConflictError

router = APIRouter(prefix="/consents", tags=["consents"])


@router.get("", response_model=SuccessResponse[ConsentOverviewOut])
async def current_consents(current_user: CurrentUser, service: ConsentServiceDep):
    return success(
        ConsentOverviewOut(
            core_processing=CoreProcessingOut(), consents=await service.current(current_user.id)
        )
    )


@router.post(
    "/{purpose}/{decision}",
    response_model=SuccessResponse[ConsentStateOut],
    status_code=status.HTTP_201_CREATED,
)
async def decide_consent(
    purpose: str,
    decision: Literal["grant", "withdraw"],
    payload: ConsentDecisionRequest,
    current_user: CurrentUser,
    service: ConsentServiceDep,
):
    try:
        state = await service.record(
            current_user.id,
            purpose=purpose,
            granted=decision == "grant",
            idempotency_key=payload.idempotency_key,
            locale=payload.locale,
            notice_version=payload.notice_version,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": str(exc)}) from exc
    except ConsentWriteConflictError as exc:
        raise HTTPException(status_code=409, detail={"code": "CONSENT_WRITE_CONFLICT"}) from exc
    return success(state, message="Consent decision recorded")
