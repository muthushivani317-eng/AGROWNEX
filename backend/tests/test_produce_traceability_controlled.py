from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from app.modules.auth.dependencies import TesterContext as ControlledTesterContext
from app.modules.auth.models import User
from app.modules.farms.models import Farm
from app.modules.organic.models import OrganicFarmProfile
from app.modules.produce.models import ProduceOffer
from app.modules.produce.traceability_router import (
    add_trace_event,
    create_trace_share,
    get_traceability,
    initialize_traceability,
    public_traceability,
    revoke_trace_share,
)
from app.modules.produce.traceability_schemas import (
    CultivationClassification,
    TraceEventCreate,
    TraceShareCreate,
    TraceShareRevoke,
)
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_farmer_trace_events_are_append_only_hash_chained_and_unverified(db_session):
    user = User(firebase_uid=f"trace-{uuid.uuid4()}", status="active")
    db_session.add(user)
    await db_session.flush()
    farm = Farm(user_id=user.id, name="Trace farm")
    db_session.add(farm)
    await db_session.flush()
    offer = ProduceOffer(
        user_id=user.id,
        farm_id=farm.id,
        crop_name="Paddy",
        quantity=10,
        unit="quintal",
        expected_harvest_date=date(2026, 8, 20),
        currency="INR",
        status="submitted",
    )
    db_session.add(offer)
    await db_session.flush()
    tester = ControlledTesterContext(user=user, role="kvk_reviewer")

    initialized = await initialize_traceability(offer.id, tester, db_session)
    assert initialized.data.public_certificate is False
    assert initialized.data.events == []

    first = await add_trace_event(
        offer.id,
        TraceEventCreate(
            event_type="harvested",
            occurred_at=datetime.now(UTC) - timedelta(hours=2),
            notes="Farmer recorded harvest",
        ),
        tester,
        db_session,
    )
    second = await add_trace_event(
        offer.id,
        TraceEventCreate(
            event_type="packed",
            occurred_at=datetime.now(UTC) - timedelta(hours=1),
        ),
        tester,
        db_session,
    )
    assert len(second.data.events) == 2
    assert first.data.events[0].event_hash != second.data.events[1].event_hash
    assert all(event.independently_verified is False for event in second.data.events)
    assert (await get_traceability(offer.id, tester, db_session)).data.batch_code.startswith("AGW-")


def test_trace_event_timestamp_requires_timezone():
    with pytest.raises(ValueError):
        TraceEventCreate(event_type="stored", occurred_at=datetime(2026, 8, 13, 9))


@pytest.mark.asyncio
async def test_certified_classification_requires_current_verified_profile(db_session):
    user = User(firebase_uid=f"cert-trace-{uuid.uuid4()}", status="active")
    db_session.add(user)
    await db_session.flush()
    farm = Farm(user_id=user.id, name="Certified trace farm")
    db_session.add(farm)
    await db_session.flush()
    offer = ProduceOffer(
        user_id=user.id,
        farm_id=farm.id,
        crop_name="Paddy",
        quantity=1,
        unit="quintal",
        currency="INR",
        status="submitted",
    )
    db_session.add(offer)
    await db_session.flush()
    tester = ControlledTesterContext(user=user, role="kvk_reviewer")
    with pytest.raises(HTTPException) as exc:
        await initialize_traceability(
            offer.id, tester, db_session, CultivationClassification.CERTIFIED_ORGANIC
        )
    assert exc.value.detail["code"] == "CERTIFIED_ORGANIC_REQUIRES_VERIFICATION"

    profile = OrganicFarmProfile(
        farm_id=farm.id,
        mode="fully_organic",
        certification_status="verified",
        certificate_expires_on=date.today() + timedelta(days=30),
        certification_verified_at=datetime.now(UTC),
        plan_version=2,
    )
    db_session.add(profile)
    await db_session.flush()
    result = await initialize_traceability(
        offer.id, tester, db_session, CultivationClassification.CERTIFIED_ORGANIC
    )
    assert result.data.certification_verified_snapshot is True
    assert result.data.organic_profile_snapshot["plan_version"] == 2


@pytest.mark.asyncio
async def test_public_share_is_allowlisted_idempotent_private_and_revocable(
    db_session, monkeypatch
):
    from app.modules.produce import traceability_router

    user = User(firebase_uid=f"share-{uuid.uuid4()}", status="active")
    db_session.add(user)
    await db_session.flush()
    farm = Farm(user_id=user.id, name="Private farm")
    db_session.add(farm)
    await db_session.flush()
    offer = ProduceOffer(
        user_id=user.id,
        farm_id=farm.id,
        crop_name="Paddy",
        quantity=1,
        unit="quintal",
        currency="INR",
        status="submitted",
    )
    db_session.add(offer)
    await db_session.flush()
    tester = ControlledTesterContext(user=user, role="kvk_reviewer")
    await initialize_traceability(offer.id, tester, db_session)
    await add_trace_event(
        offer.id,
        TraceEventCreate(
            event_type="harvested",
            occurred_at=datetime.now(UTC) - timedelta(hours=1),
            notes="PRIVATE NOTE",
            location_text="Exact private field",
            evidence_url="https://private.test/a",
        ),
        tester,
        db_session,
    )
    monkeypatch.setattr(traceability_router.settings, "public_api_url", "https://api.example.test")
    payload = TraceShareCreate(
        consent_fields=["classification", "events"], idempotency_key="share-create-0001"
    )
    first = await create_trace_share(offer.id, payload, tester, db_session)
    replay = await create_trace_share(offer.id, payload, tester, db_session)
    assert first.data.share_url == replay.data.share_url == first.data.qr_payload
    token = str(first.data.share_url).rsplit("/", 1)[-1]
    public = (await public_traceability(token, db_session)).data.model_dump()
    assert public["events"] == [
        {
            "event_type": "harvested",
            "occurred_at": public["events"][0]["occurred_at"],
        }
    ]
    serialized = str(public)
    secrets = (str(user.id), str(farm.id), "PRIVATE NOTE", "Exact private field", "private.test")
    for secret in secrets:
        assert secret not in serialized
    await revoke_trace_share(
        offer.id, TraceShareRevoke(idempotency_key="share-revoke-0001"), tester, db_session
    )
    with pytest.raises(HTTPException) as exc:
        await public_traceability(token, db_session)
    assert exc.value.status_code == 404
