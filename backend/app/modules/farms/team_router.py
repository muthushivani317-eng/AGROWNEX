from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.auth.constants import UserStatus
from app.modules.auth.dependencies import ControlledTester
from app.modules.auth.models import User
from app.modules.farms.models import FarmTeamMember
from app.modules.farms.repositories import FarmRepository
from app.modules.farms.team_schemas import FarmTeamMemberCreate, FarmTeamMemberOut
from app.schemas.response import SuccessResponse, success

router = APIRouter(prefix="/farms", tags=["farm-team-controlled"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def _owned_farm(session: AsyncSession, farm_id: uuid.UUID, user_id: uuid.UUID):
    farm = await FarmRepository(session).get_for_user(farm_id, user_id)
    if farm is None:
        raise HTTPException(status_code=404, detail={"code": "FARM_NOT_FOUND"})
    return farm


def _out(row: FarmTeamMember, phone: str) -> FarmTeamMemberOut:
    return FarmTeamMemberOut(
        id=row.id,
        user_id=row.user_id,
        phone_number=phone,
        role=row.role,
        created_at=row.created_at,
    )


@router.get(
    "/{farm_id}/team-controlled",
    response_model=SuccessResponse[list[FarmTeamMemberOut]],
)
async def list_team(
    farm_id: uuid.UUID, tester: ControlledTester, session: SessionDep
):
    await _owned_farm(session, farm_id, tester.user.id)
    result = await session.execute(
        select(FarmTeamMember, User.phone_number)
        .join(User, User.id == FarmTeamMember.user_id)
        .where(FarmTeamMember.farm_id == farm_id)
        .order_by(FarmTeamMember.created_at.asc())
    )
    return success([_out(row, phone or "") for row, phone in result.all()])


@router.post(
    "/{farm_id}/team-controlled",
    response_model=SuccessResponse[FarmTeamMemberOut],
    status_code=201,
)
async def add_team_member(
    farm_id: uuid.UUID,
    payload: FarmTeamMemberCreate,
    tester: ControlledTester,
    session: SessionDep,
):
    await _owned_farm(session, farm_id, tester.user.id)
    result = await session.execute(
        select(User).where(
            User.phone_number == payload.phone_number,
            User.status == UserStatus.ACTIVE,
            User.is_deleted.is_(False),
        )
    )
    member_user = result.scalar_one_or_none()
    if member_user is None:
        raise HTTPException(status_code=422, detail={"code": "TEAM_ACCOUNT_NOT_FOUND"})
    if member_user.id == tester.user.id:
        raise HTTPException(status_code=422, detail={"code": "FARM_OWNER_ALREADY_INCLUDED"})
    row = FarmTeamMember(
        farm_id=farm_id,
        user_id=member_user.id,
        role=payload.role.value,
        added_by=tester.user.id,
    )
    session.add(row)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail={"code": "TEAM_MEMBER_EXISTS"}) from exc
    return success(_out(row, member_user.phone_number or ""), message="Team member added")


@router.delete(
    "/{farm_id}/team-controlled/{member_id}",
    response_model=SuccessResponse[None],
)
async def remove_team_member(
    farm_id: uuid.UUID,
    member_id: uuid.UUID,
    tester: ControlledTester,
    session: SessionDep,
):
    await _owned_farm(session, farm_id, tester.user.id)
    result = await session.execute(
        select(FarmTeamMember).where(
            FarmTeamMember.id == member_id,
            FarmTeamMember.farm_id == farm_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "TEAM_MEMBER_NOT_FOUND"})
    await session.delete(row)
    await session.flush()
    return success(None, message="Team member removed")
