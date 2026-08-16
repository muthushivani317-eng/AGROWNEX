from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.auth.dependencies import ControlledTester
from app.modules.equipment.models import EquipmentListing, EquipmentRequest
from app.modules.equipment.schemas import (
    EquipmentDecision,
    EquipmentListingCreate,
    EquipmentListingOut,
    EquipmentRequestCreate,
    EquipmentRequestOut,
)
from app.modules.farms.repositories import FarmRepository
from app.schemas.response import SuccessResponse, success

router = APIRouter(prefix="/equipment-controlled", tags=["equipment-controlled"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


def listing_out(row: EquipmentListing) -> EquipmentListingOut:
    return EquipmentListingOut.model_validate(row, from_attributes=True)


def request_out(
    row: EquipmentRequest,
    name: str,
    *,
    viewer_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> EquipmentRequestOut:
    return EquipmentRequestOut(
        id=row.id, listing_id=row.listing_id, equipment_name=name,
        requester_user_id=row.requester_user_id, farm_id=row.farm_id,
        start_date=row.start_date, end_date=row.end_date, purpose=row.purpose,
        status=row.status, decision_note=row.decision_note, created_at=row.created_at,
        can_decide=owner_id == viewer_id and row.status == "pending",
        is_requester=row.requester_user_id == viewer_id,
    )


@router.get("", response_model=SuccessResponse[list[EquipmentListingOut]])
async def list_equipment(
    _: ControlledTester,
    session: SessionDep,
    district: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    stmt = select(EquipmentListing).where(
        EquipmentListing.is_deleted.is_(False), EquipmentListing.status == "available"
    )
    if district:
        stmt = stmt.where(EquipmentListing.district == district)
    stmt = (
        stmt.order_by(EquipmentListing.created_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    rows = (await session.execute(stmt)).scalars()
    return success([listing_out(row) for row in rows.all()])


@router.post("", response_model=SuccessResponse[EquipmentListingOut], status_code=201)
async def create_equipment(
    payload: EquipmentListingCreate, tester: ControlledTester, session: SessionDep
):
    row = EquipmentListing(owner_user_id=tester.user.id, **payload.model_dump())
    session.add(row)
    await session.flush()
    return success(listing_out(row), message="Equipment listing created")


@router.post(
    "/{listing_id}/requests",
    response_model=SuccessResponse[EquipmentRequestOut],
    status_code=201,
)
async def request_equipment(
    listing_id: uuid.UUID,
    payload: EquipmentRequestCreate,
    tester: ControlledTester,
    session: SessionDep,
):
    listing = await session.get(EquipmentListing, listing_id)
    if listing is None or listing.is_deleted or listing.status != "available":
        raise HTTPException(404, detail={"code": "EQUIPMENT_NOT_AVAILABLE"})
    if listing.owner_user_id == tester.user.id:
        raise HTTPException(422, detail={"code": "CANNOT_REQUEST_OWN_EQUIPMENT"})
    if payload.start_date < datetime.now(UTC).date():
        raise HTTPException(422, detail={"code": "EQUIPMENT_DATE_IN_PAST"})
    if await FarmRepository(session).get_for_user(payload.farm_id, tester.user.id) is None:
        raise HTTPException(404, detail={"code": "FARM_NOT_FOUND"})
    overlap = await session.execute(
        select(EquipmentRequest.id).where(
            EquipmentRequest.listing_id == listing_id,
            EquipmentRequest.status == "approved",
            EquipmentRequest.start_date <= payload.end_date,
            EquipmentRequest.end_date >= payload.start_date,
        )
    )
    if overlap.first():
        raise HTTPException(409, detail={"code": "EQUIPMENT_DATES_UNAVAILABLE"})
    row = EquipmentRequest(
        listing_id=listing_id, requester_user_id=tester.user.id, **payload.model_dump()
    )
    session.add(row)
    await session.flush()
    return success(
        request_out(
            row,
            listing.name,
            viewer_id=tester.user.id,
            owner_id=listing.owner_user_id,
        ),
        message="Equipment request sent",
    )


@router.get("/requests/mine", response_model=SuccessResponse[list[EquipmentRequestOut]])
async def my_requests(
    tester: ControlledTester,
    session: SessionDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    result = await session.execute(
        select(EquipmentRequest, EquipmentListing.name, EquipmentListing.owner_user_id)
        .join(EquipmentListing, EquipmentListing.id == EquipmentRequest.listing_id)
        .where(
            or_(
                EquipmentRequest.requester_user_id == tester.user.id,
                EquipmentListing.owner_user_id == tester.user.id,
            )
        )
        .order_by(EquipmentRequest.created_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    return success([
        request_out(row, name, viewer_id=tester.user.id, owner_id=owner_id)
        for row, name, owner_id in result.all()
    ])


@router.patch(
    "/requests/{request_id}/decision",
    response_model=SuccessResponse[EquipmentRequestOut],
)
async def decide_request(
    request_id: uuid.UUID,
    payload: EquipmentDecision,
    tester: ControlledTester,
    session: SessionDep,
):
    result = await session.execute(
        select(EquipmentRequest, EquipmentListing)
        .join(EquipmentListing, EquipmentListing.id == EquipmentRequest.listing_id)
        .where(EquipmentRequest.id == request_id)
        .with_for_update()
    )
    pair = result.first()
    if pair is None or pair[1].owner_user_id != tester.user.id:
        raise HTTPException(404, detail={"code": "EQUIPMENT_REQUEST_NOT_FOUND"})
    row, listing = pair
    if row.status != "pending":
        raise HTTPException(409, detail={"code": "EQUIPMENT_REQUEST_ALREADY_DECIDED"})
    if payload.decision == "approved":
        overlap = await session.execute(
            select(EquipmentRequest.id).where(
                EquipmentRequest.id != row.id,
                EquipmentRequest.listing_id == row.listing_id,
                EquipmentRequest.status == "approved",
                EquipmentRequest.start_date <= row.end_date,
                EquipmentRequest.end_date >= row.start_date,
            )
        )
        if overlap.first():
            raise HTTPException(
                409, detail={"code": "EQUIPMENT_DATES_UNAVAILABLE"}
            )
    row.status = payload.decision
    row.decision_note = payload.note
    row.decided_by = tester.user.id
    await session.flush()
    return success(
        request_out(
            row,
            listing.name,
            viewer_id=tester.user.id,
            owner_id=listing.owner_user_id,
        ),
        message="Equipment request updated",
    )
