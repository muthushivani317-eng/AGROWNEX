"""Farm API routes (docs/API_CONTRACT.md → FARM MODULE).

    GET    /farms                 POST   /farms
    GET    /farms/{id}            PUT    /farms/{id}     DELETE /farms/{id}
    GET    /farms/{id}/boundary   PUT    /farms/{id}/boundary
    GET    /farms/{id}/images     POST   /farms/{id}/images

Every route is authenticated and thin — all logic lives in ``FarmService``.
"""
from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Query

from app.modules.farms.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.modules.farms.dependencies import CurrentUser, FarmServiceDep
from app.modules.farms.schemas import (
    BoundaryIn,
    BoundaryOut,
    FarmMediaCreate,
    FarmMediaOut,
    FarmOut,
    FarmSummaryOut,
    FarmWrite,
)
from app.schemas.response import PaginatedData, SuccessResponse, success

router = APIRouter(prefix="/farms", tags=["farms"])


# ----- Collection -----
@router.get("", response_model=SuccessResponse[PaginatedData[FarmSummaryOut]])
async def list_farms(
    current_user: CurrentUser,
    service: FarmServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    status: str | None = Query(None),
    district: str | None = Query(None),
    crop: str | None = Query(None),
    q: str | None = Query(None),
    sort: str = Query("updated_at"),
    order: str = Query("desc"),
):
    """List the farmer's farms (paginated, filterable)."""
    items, total = await service.list_farms(
        current_user,
        page=page,
        page_size=page_size,
        status=status,
        district=district,
        crop=crop,
        search=q,
        sort=sort,
        order=order,
    )
    data = PaginatedData(
        items=[FarmSummaryOut.from_farm(farm) for farm in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=math.ceil(total / page_size) if page_size else 0,
    )
    return success(data)


@router.post("", response_model=SuccessResponse[FarmOut], status_code=201)
async def create_farm(
    payload: FarmWrite, current_user: CurrentUser, service: FarmServiceDep
):
    """Register a new farm (with optional location and boundary)."""
    farm = await service.create_farm(current_user, payload)
    return success(FarmOut.from_farm(farm), message="Farm created")


# ----- Item -----
@router.get("/{farm_id}", response_model=SuccessResponse[FarmOut])
async def get_farm(
    farm_id: uuid.UUID, current_user: CurrentUser, service: FarmServiceDep
):
    """Fetch a single farm with its location, boundary and images."""
    farm = await service.get_farm(current_user, farm_id)
    return success(FarmOut.from_farm(farm))


@router.put("/{farm_id}", response_model=SuccessResponse[FarmOut])
async def update_farm(
    farm_id: uuid.UUID,
    payload: FarmWrite,
    current_user: CurrentUser,
    service: FarmServiceDep,
):
    """Update a farm."""
    farm = await service.update_farm(current_user, farm_id, payload)
    return success(FarmOut.from_farm(farm), message="Farm updated")


@router.delete("/{farm_id}", response_model=SuccessResponse[None])
async def delete_farm(
    farm_id: uuid.UUID, current_user: CurrentUser, service: FarmServiceDep
):
    """Soft-delete a farm."""
    await service.delete_farm(current_user, farm_id)
    return success(None, message="Farm deleted")


# ----- Boundary -----
@router.get("/{farm_id}/boundary", response_model=SuccessResponse[BoundaryOut | None])
async def get_boundary(
    farm_id: uuid.UUID, current_user: CurrentUser, service: FarmServiceDep
):
    """Return the farm's boundary polygon (or null if none)."""
    boundary = await service.get_boundary(current_user, farm_id)
    return success(BoundaryOut.model_validate(boundary) if boundary else None)


@router.put("/{farm_id}/boundary", response_model=SuccessResponse[BoundaryOut])
async def update_boundary(
    farm_id: uuid.UUID,
    payload: BoundaryIn,
    current_user: CurrentUser,
    service: FarmServiceDep,
):
    """Create or replace the farm's boundary; area is recomputed server-side."""
    boundary = await service.update_boundary(current_user, farm_id, payload)
    return success(BoundaryOut.model_validate(boundary), message="Boundary saved")


# ----- Images -----
@router.get("/{farm_id}/images", response_model=SuccessResponse[list[FarmMediaOut]])
async def list_images(
    farm_id: uuid.UUID, current_user: CurrentUser, service: FarmServiceDep
):
    """List the farm's images."""
    images = await service.list_images(current_user, farm_id)
    return success([FarmMediaOut.model_validate(m) for m in images])


@router.post(
    "/{farm_id}/images",
    response_model=SuccessResponse[FarmMediaOut],
    status_code=201,
)
async def add_image(
    farm_id: uuid.UUID,
    payload: FarmMediaCreate,
    current_user: CurrentUser,
    service: FarmServiceDep,
):
    """Attach an uploaded image (S3 URL + metadata) to the farm."""
    media = await service.add_image(current_user, farm_id, payload)
    return success(FarmMediaOut.model_validate(media), message="Image added")
