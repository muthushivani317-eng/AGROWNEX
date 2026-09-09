from datetime import UTC, datetime

import pytest
from app.api.v1.router import api_router
from app.modules.action_verification.schemas import ActionCreateIn, ActionRespondIn
from app.modules.action_verification.service import ActionVerificationService
from app.modules.auth.models import User
from app.modules.farms.models import Farm
from app.modules.organic_logbook.exceptions import (
    OrganicLogEntryNotFoundError,
    OrganicLogReferenceError,
)
from app.modules.organic_logbook.schemas import OrganicEvidenceIn, OrganicLogCreateIn
from app.modules.organic_logbook.service import OrganicLogbookService
from fastapi import FastAPI


async def _owner(db_session, suffix="owner"):
    user = User(firebase_uid=f"organic-log-{suffix}", status="active")
    db_session.add(user)
    await db_session.flush()
    farm = Farm(user_id=user.id, name="Organic log farm", crop="paddy", status="active")
    db_session.add(farm)
    await db_session.flush()
    return user, farm


def _payload(farm, **overrides):
    values = dict(
        farm_id=farm.id,
        practice_type="mulching",
        practice_code="apply_crop_residue_mulch",
        occurred_at=datetime.now(UTC),
        idempotency_key="offline-event-0001",
    )
    values.update(overrides)
    return OrganicLogCreateIn(**values)


@pytest.mark.asyncio
async def test_manual_log_is_farmer_reported_and_idempotent(db_session):
    user, farm = await _owner(db_session)
    service = OrganicLogbookService(db_session)
    payload = _payload(
        farm,
        evidence=[OrganicEvidenceIn(
            evidence_type="photo",
            storage_ref=f"organic-evidence/{user.id}/{farm.id}/photo-1.jpg",
        )],
    )

    first = await service.create(user, payload)
    second = await service.create(user, payload)

    assert first.id == second.id
    assert first.verification_status == "farmer_reported"
    assert first.expert_reviewed is False
    assert first.source_verified is False
    assert first.evidence[0].farmer_reported is True
    assert first.evidence[0].expert_reviewed is False


@pytest.mark.asyncio
async def test_linked_action_preserves_source_but_not_expert_verification(db_session):
    user, farm = await _owner(db_session, "linked")
    actions = ActionVerificationService(db_session)
    action = await actions.create(
        user,
        ActionCreateIn(
            farm_id=farm.id,
            source_feature="organic_calendar",
            source_record_id="paddy:day-20:mulch",
            source_version="tnau-2026-1",
            action_code="apply_mulch",
            suggestion_time=datetime.now(UTC),
        ),
    )
    await actions.respond(
        user,
        action.id,
        ActionRespondIn(
            event="done", expected_version=1,
            idempotency_key="action-done-0001", request_id="request-1",
        ),
    )

    row = await OrganicLogbookService(db_session).create(
        user, _payload(farm, action_workflow_id=action.id, idempotency_key="linked-log-0001")
    )

    assert row.source_feature == "organic_calendar"
    assert row.source_record_id == "paddy:day-20:mulch"
    assert row.verification_status == "farmer_reported"
    assert row.expert_reviewed is False


@pytest.mark.asyncio
async def test_logbook_is_owner_isolated(db_session):
    owner, farm = await _owner(db_session, "isolation-owner")
    other, _ = await _owner(db_session, "isolation-other")
    row = await OrganicLogbookService(db_session).create(owner, _payload(farm))

    assert await OrganicLogbookService(db_session).list(other) == []
    with pytest.raises(OrganicLogEntryNotFoundError):
        await OrganicLogbookService(db_session).get(other, row.id)


def test_organic_logbook_routes_are_registered():
    app = FastAPI()
    app.include_router(api_router)
    paths = app.openapi()["paths"]
    assert "post" in paths["/organic-logbook/entries"]
    assert "get" in paths["/organic-logbook/entries"]
    assert "get" in paths["/organic-logbook/entries/{entry_id}"]


@pytest.mark.asyncio
async def test_evidence_cannot_reference_another_storage_namespace(db_session):
    user, farm = await _owner(db_session, "evidence-scope")
    with pytest.raises(OrganicLogReferenceError):
        await OrganicLogbookService(db_session).create(
            user,
            _payload(
                farm,
                evidence=[
                    OrganicEvidenceIn(
                        evidence_type="photo",
                        storage_ref="organic-evidence/other/farm/photo.jpg",
                    )
                ],
            ),
        )
