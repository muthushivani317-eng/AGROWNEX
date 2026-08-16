import uuid

from fastapi import APIRouter, HTTPException, Query

from app.modules.auth.dependencies import CurrentUser
from app.schemas.response import SuccessResponse, success

from .dependencies import DiseaseRiskServiceDep
from .schemas import RiskAlertOut, RiskEvaluateRequest, RiskListOut
from .service import ACTIVE_RULE_REGISTRY

router = APIRouter(prefix="/disease-risk", tags=["disease-risk"])


def _out(row, *, cached: bool = False) -> RiskAlertOut:
    return RiskAlertOut.model_validate({**row.__dict__, "id": row.id, "cached": cached})


@router.post("/evaluate", response_model=SuccessResponse[RiskAlertOut])
async def evaluate(
    payload: RiskEvaluateRequest, current_user: CurrentUser, service: DiseaseRiskServiceDep
):
    try:
        return success(
            _out(
                await service.evaluate(
                    current_user, payload.farm_id, payload.crop_cycle_id, payload.idempotency_key
                )
            )
        )
    except PermissionError as exc:
        raise HTTPException(404, detail={"code": str(exc)}) from exc


@router.get("/current", response_model=SuccessResponse[RiskAlertOut | None])
async def current(farm_id: uuid.UUID, current_user: CurrentUser, service: DiseaseRiskServiceDep):
    try:
        row = await service.current(current_user, farm_id)
        return success(_out(row, cached=True) if row else None)
    except PermissionError as exc:
        raise HTTPException(404, detail={"code": str(exc)}) from exc


@router.get("/history", response_model=SuccessResponse[RiskListOut])
async def history(
    current_user: CurrentUser,
    service: DiseaseRiskServiceDep,
    farm_id: uuid.UUID | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    try:
        items, total = await service.history(current_user, farm_id, limit, offset)
        return success(
            RiskListOut(
                items=[_out(x, cached=True) for x in items],
                total=total,
                active_verified_rule_count=len(ACTIVE_RULE_REGISTRY.active),
            )
        )
    except PermissionError as exc:
        raise HTTPException(404, detail={"code": str(exc)}) from exc


@router.get("/{risk_id}", response_model=SuccessResponse[RiskAlertOut])
async def detail(risk_id: uuid.UUID, current_user: CurrentUser, service: DiseaseRiskServiceDep):
    try:
        return success(_out(await service.get(current_user, risk_id), cached=True))
    except LookupError as exc:
        raise HTTPException(404, detail={"code": str(exc)}) from exc


@router.patch("/{risk_id}/acknowledge", response_model=SuccessResponse[RiskAlertOut])
async def acknowledge(
    risk_id: uuid.UUID, current_user: CurrentUser, service: DiseaseRiskServiceDep
):
    try:
        return success(_out(await service.acknowledge(current_user, risk_id), cached=True))
    except LookupError as exc:
        raise HTTPException(404, detail={"code": str(exc)}) from exc
