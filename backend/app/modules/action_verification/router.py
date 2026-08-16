import uuid

from fastapi import APIRouter, HTTPException, Query

from app.schemas.response import SuccessResponse, success

from .dependencies import ActionVerificationServiceDep, CurrentUser
from .schemas import ActionCreateIn, ActionHistoryOut, ActionOut, ActionRespondIn

router = APIRouter(prefix="/action-verification", tags=["action-verification"])


@router.get("/actions", response_model=SuccessResponse[list[ActionOut]])
async def actions(
    current_user: CurrentUser, service: ActionVerificationServiceDep, pending: bool = Query(False)
):
    return success(
        [ActionOut.from_row(row) for row in await service.list(current_user, pending_only=pending)]
    )


@router.post("/actions", response_model=SuccessResponse[ActionOut], status_code=201)
async def create(
    payload: ActionCreateIn, current_user: CurrentUser, service: ActionVerificationServiceDep
):
    return success(ActionOut.from_row(await service.create(current_user, payload)))


@router.get("/actions/{action_id}", response_model=SuccessResponse[ActionOut])
async def detail(
    action_id: uuid.UUID, current_user: CurrentUser, service: ActionVerificationServiceDep
):
    return success(ActionOut.from_row(await service.get(current_user, action_id)))


@router.post("/actions/{action_id}/responses", response_model=SuccessResponse[ActionOut])
async def respond(
    action_id: uuid.UUID,
    payload: ActionRespondIn,
    current_user: CurrentUser,
    service: ActionVerificationServiceDep,
):
    try:
        row = await service.respond(current_user, action_id, payload)
    except ValueError as exc:
        raise HTTPException(409, detail={"code": str(exc)}) from exc
    return success(ActionOut.from_row(row))


@router.get("/actions/{action_id}/history", response_model=SuccessResponse[list[ActionHistoryOut]])
async def history(
    action_id: uuid.UUID, current_user: CurrentUser, service: ActionVerificationServiceDep
):
    return success(
        [ActionHistoryOut.from_row(row) for row in await service.history(current_user, action_id)]
    )
