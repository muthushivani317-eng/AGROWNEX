from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.modules.auth.constants import UserStatus
from app.modules.auth.dependencies import TesterContext as ControlledTesterContext
from app.modules.auth.models import User
from app.modules.equipment.router import (
    create_equipment,
    decide_request,
    my_requests,
    request_equipment,
)
from app.modules.equipment.schemas import (
    EquipmentDecision,
    EquipmentListingCreate,
    EquipmentRequestCreate,
)
from app.modules.farms.models import Farm
from fastapi import HTTPException


async def user(db_session, phone: str) -> User:
    row = User(
        firebase_uid=f"equipment-{uuid.uuid4()}",
        phone_number=phone,
        status=UserStatus.ACTIVE,
    )
    db_session.add(row)
    await db_session.flush()
    return row


@pytest.mark.asyncio
async def test_listing_request_and_owner_decision_have_no_payment_contract(db_session):
    owner = await user(db_session, "+919100000001")
    requester = await user(db_session, "+919100000002")
    farm = Farm(user_id=requester.id, name="Request farm")
    db_session.add(farm)
    await db_session.flush()
    owner_context = ControlledTesterContext(user=owner, role="kvk_reviewer")
    requester_context = ControlledTesterContext(user=requester, role="pilot_tester")

    listing_response = await create_equipment(
        EquipmentListingCreate(name="Village tractor", equipment_type="tractor"),
        owner_context,
        db_session,
    )
    listing = listing_response.data
    assert listing.payments_supported is False

    tomorrow = datetime.now(UTC).date() + timedelta(days=1)
    request_response = await request_equipment(
        listing.id,
        EquipmentRequestCreate(
            farm_id=farm.id,
            start_date=tomorrow,
            end_date=tomorrow + timedelta(days=1),
        ),
        requester_context,
        db_session,
    )
    request = request_response.data
    assert request.payment_status == "not_supported"
    assert request.is_requester is True
    assert request.can_decide is False

    # page/page_size must be passed explicitly here: my_requests is called
    # directly (not through FastAPI's request handling), so its Query(...)
    # defaults are never resolved to plain ints -- calling it with no
    # override left `page_size` as the raw Query object, which broke
    # `.limit(page_size)` (2026-08 pagination addition; same convention
    # other flow tests already use for paginated service calls).
    incoming = (
        await my_requests(owner_context, db_session, page=1, page_size=20)
    ).data[0]
    assert incoming.can_decide is True
    decided = await decide_request(
        incoming.id,
        EquipmentDecision(decision="approved"),
        owner_context,
        db_session,
    )
    assert decided.data.status == "approved"
    assert decided.data.can_decide is False


@pytest.mark.asyncio
async def test_requester_cannot_decide_own_request(db_session):
    owner = await user(db_session, "+919100000003")
    requester = await user(db_session, "+919100000004")
    farm = Farm(user_id=requester.id, name="Second farm")
    db_session.add(farm)
    await db_session.flush()
    owner_context = ControlledTesterContext(user=owner, role="internal_tester")
    requester_context = ControlledTesterContext(user=requester, role="pilot_tester")
    listing = (
        await create_equipment(
            EquipmentListingCreate(name="Power tiller", equipment_type="tiller"),
            owner_context,
            db_session,
        )
    ).data
    tomorrow = datetime.now(UTC).date() + timedelta(days=1)
    request = (
        await request_equipment(
            listing.id,
            EquipmentRequestCreate(farm_id=farm.id, start_date=tomorrow, end_date=tomorrow),
            requester_context,
            db_session,
        )
    ).data
    with pytest.raises(HTTPException) as error:
        await decide_request(
            request.id,
            EquipmentDecision(decision="approved"),
            requester_context,
            db_session,
        )
    assert error.value.status_code == 404
