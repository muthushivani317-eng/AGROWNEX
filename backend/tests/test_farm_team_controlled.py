from __future__ import annotations

import uuid

import pytest
from app.modules.auth.constants import UserStatus
from app.modules.auth.dependencies import TesterContext as ControlledTesterContext
from app.modules.auth.models import User
from app.modules.farms.models import Farm
from app.modules.farms.team_router import add_team_member, list_team, remove_team_member
from app.modules.farms.team_schemas import FarmTeamMemberCreate, FarmTeamRole
from fastapi import HTTPException


async def make_user(db_session, phone: str) -> User:
    user = User(
        firebase_uid=f"team-{uuid.uuid4()}",
        phone_number=phone,
        status=UserStatus.ACTIVE,
        is_phone_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.mark.asyncio
async def test_owner_can_add_list_and_remove_roster_member(db_session):
    owner = await make_user(db_session, "+919000000001")
    member = await make_user(db_session, "+919000000002")
    farm = Farm(user_id=owner.id, name="Pilot farm")
    db_session.add(farm)
    await db_session.flush()
    tester = ControlledTesterContext(user=owner, role="kvk_reviewer")

    created = await add_team_member(
        farm.id,
        FarmTeamMemberCreate(
            phone_number=member.phone_number,
            role=FarmTeamRole.FIELD_WORKER,
        ),
        tester,
        db_session,
    )
    assert created.data.user_id == member.id
    assert created.data.grants_farm_data_access is False
    assert created.data.test_mode is True

    listed = await list_team(farm.id, tester, db_session)
    assert [row.user_id for row in listed.data] == [member.id]

    await remove_team_member(farm.id, created.data.id, tester, db_session)
    assert (await list_team(farm.id, tester, db_session)).data == []


@pytest.mark.asyncio
async def test_tester_cannot_manage_another_owners_farm(db_session):
    owner = await make_user(db_session, "+919000000003")
    other = await make_user(db_session, "+919000000004")
    farm = Farm(user_id=owner.id, name="Private farm")
    db_session.add(farm)
    await db_session.flush()

    with pytest.raises(HTTPException) as error:
        await list_team(
            farm.id,
            ControlledTesterContext(user=other, role="internal_tester"),
            db_session,
        )
    assert error.value.status_code == 404


def test_phone_requires_explicit_international_format():
    with pytest.raises(ValueError):
        FarmTeamMemberCreate(phone_number="9000000002", role="observer")
