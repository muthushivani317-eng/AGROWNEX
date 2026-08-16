from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.modules.produce.harvest_readiness_dependencies import (
    CurrentUser,
    HarvestReadinessServiceDep,
)
from app.modules.produce.harvest_readiness_schemas import (
    HarvestReadinessConfirmIn,
    HarvestReadinessEvaluateIn,
    HarvestReadinessHistoryOut,
    HarvestReadinessOut,
)
from app.schemas.response import SuccessResponse, success

router = APIRouter(prefix="/harvest-readiness", tags=["harvest-readiness"])


@router.post(
    "/evaluate",
    response_model=SuccessResponse[HarvestReadinessOut],
    status_code=status.HTTP_201_CREATED,
)
async def evaluate(
    payload: HarvestReadinessEvaluateIn,
    current_user: CurrentUser,
    service: HarvestReadinessServiceDep,
):
    row = await service.evaluate(
        current_user,
        farm_id=payload.farm_id,
        crop_cycle_id=payload.crop_cycle_id,
        observations=tuple(payload.farmer_observations),
        weather_freshness=payload.weather_freshness,
        idempotency_key=payload.idempotency_key,
    )
    return success(HarvestReadinessOut.from_row(row))


@router.get("/current", response_model=SuccessResponse[HarvestReadinessOut | None])
async def current(
    current_user: CurrentUser,
    service: HarvestReadinessServiceDep,
    farm_id: uuid.UUID = Query(...),
    crop_cycle_id: str = Query(..., min_length=1, max_length=80),
):
    row = await service.current(current_user, farm_id, crop_cycle_id)
    return success(HarvestReadinessOut.from_row(row) if row else None)


@router.get(
    "/{readiness_id}/history",
    response_model=SuccessResponse[list[HarvestReadinessHistoryOut]],
)
async def history(
    readiness_id: uuid.UUID,
    current_user: CurrentUser,
    service: HarvestReadinessServiceDep,
):
    return success(
        [
            HarvestReadinessHistoryOut.from_row(row)
            for row in await service.history(current_user, readiness_id)
        ]
    )


@router.post("/confirm", response_model=SuccessResponse[HarvestReadinessOut])
async def confirm(
    payload: HarvestReadinessConfirmIn,
    current_user: CurrentUser,
    service: HarvestReadinessServiceDep,
):
    try:
        row = await service.confirm(
            current_user,
            record_id=payload.readiness_id,
            ready=payload.ready,
            idempotency_key=payload.idempotency_key,
            note=payload.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": str(exc)}) from exc
    return success(HarvestReadinessOut.from_row(row))
