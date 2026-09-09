import uuid

from fastapi import APIRouter, HTTPException, Query

from app.schemas.response import SuccessResponse, success

from .dependencies import CurrentUser, OrganicLogbookServiceDep
from .schemas import OrganicLogCreateIn, OrganicLogOut

router = APIRouter(prefix="/organic-logbook", tags=["organic-logbook"])


@router.post("/entries", response_model=SuccessResponse[OrganicLogOut], status_code=201)
async def create_entry(
    payload: OrganicLogCreateIn,
    current_user: CurrentUser,
    service: OrganicLogbookServiceDep,
):
    try:
        row = await service.create(current_user, payload)
    except ValueError as exc:
        raise HTTPException(422, detail={"code": str(exc)}) from exc
    return success(OrganicLogOut.from_row(row), message="Organic practice recorded")


@router.get("/entries", response_model=SuccessResponse[list[OrganicLogOut]])
async def list_entries(
    current_user: CurrentUser,
    service: OrganicLogbookServiceDep,
    farm_id: uuid.UUID | None = Query(default=None),
):
    rows = await service.list(current_user, farm_id=farm_id)
    return success([OrganicLogOut.from_row(row) for row in rows])


@router.get("/entries/{entry_id}", response_model=SuccessResponse[OrganicLogOut])
async def get_entry(
    entry_id: uuid.UUID,
    current_user: CurrentUser,
    service: OrganicLogbookServiceDep,
):
    return success(OrganicLogOut.from_row(await service.get(current_user, entry_id)))
