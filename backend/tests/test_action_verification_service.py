from datetime import UTC, datetime, timedelta

import pytest
from app.modules.action_verification.exceptions import ActionNotFoundError
from app.modules.action_verification.schemas import ActionCreateIn, ActionRespondIn
from app.modules.action_verification.service import ActionVerificationService
from app.modules.action_verification.source_adapter import SourceAction
from app.modules.auth.models import User
from app.modules.farms.models import Farm


async def _owner(db_session):
    user = User(firebase_uid="action-owner", status="active")
    db_session.add(user)
    await db_session.flush()
    farm = Farm(user_id=user.id, name="Action farm", crop="paddy", status="active")
    db_session.add(farm)
    await db_session.flush()
    return user, farm


@pytest.mark.asyncio
async def test_farmer_action_done_is_persisted_as_report_only(db_session) -> None:
    user, farm = await _owner(db_session)
    service = ActionVerificationService(db_session)
    action = await service.create(
        user,
        ActionCreateIn(
            farm_id=farm.id,
            source_feature="farmer_task",
            source_record_id="manual-1",
            source_version="1",
            action_code="farmer_created_task",
            farmer_created=True,
            source_verified=False,
            suggestion_time=datetime.now(UTC),
        ),
    )
    result = await service.respond(
        user,
        action.id,
        ActionRespondIn(
            event="done",
            expected_version=1,
            idempotency_key="done-request-1",
            request_id="request-1",
        ),
    )
    assert result.status == "farmer_reported_done"
    assert result.verification_scope == "workflow_completion_only"
    assert "success" not in result.status
    assert len(await service.history(user, action.id)) == 2


@pytest.mark.asyncio
async def test_response_is_idempotent_and_cross_user_isolated(db_session) -> None:
    user, farm = await _owner(db_session)
    other = User(firebase_uid="action-other", status="active")
    db_session.add(other)
    await db_session.flush()
    service = ActionVerificationService(db_session)
    action = await service.create(
        user,
        ActionCreateIn(
            farm_id=farm.id,
            source_feature="farmer_task",
            source_record_id="manual-2",
            source_version="1",
            action_code="farmer_created_task",
            farmer_created=True,
            source_verified=False,
            suggestion_time=datetime.now(UTC),
        ),
    )
    payload = ActionRespondIn(
        event="not_done",
        expected_version=1,
        idempotency_key="not-done-request-1",
        request_id="request-2",
    )
    first = await service.respond(user, action.id, payload)
    second = await service.respond(user, action.id, payload)
    assert first.id == second.id
    assert len(await service.history(user, action.id)) == 2
    # Ownership violations are 404s (ActionNotFoundError), not PermissionError --
    # so a cross-user probe can't tell "not yours" from "doesn't exist" (see
    # app.modules.action_verification.exceptions).
    with pytest.raises(ActionNotFoundError):
        await service.respond(other, action.id, payload)


@pytest.mark.asyncio
async def test_real_weather_source_action_has_stable_identity_and_no_duplicate(db_session):
    user, farm = await _owner(db_session)
    service = ActionVerificationService(db_session)
    # Relative to "now", not a hardcoded calendar date: a fixed past
    # suggestion_time/expires_at pair silently starts failing this test the
    # moment real time catches up to it (register_source_action treats an
    # elapsed expires_at as "not actionable" -> None), which is exactly what
    # happened here (found while verifying unrelated schemes/pagination work,
    # 2026-08-16).
    now = datetime.now(UTC)
    suggestion_time = now - timedelta(hours=1)
    source = SourceAction(
        source_feature="weather_to_action",
        source_record_id=f"{farm.id}:{suggestion_time.date().isoformat()}:heavy_rain.expected",
        source_version=suggestion_time.isoformat(),
        action_code="Check drainage and hold irrigation for paddy",
        suggestion_time=suggestion_time,
        expires_at=now + timedelta(hours=23),
        source_verified=False,
    )
    first = await service.register_source_action(user, farm.id, source)
    second = await service.register_source_action(user, farm.id, source)
    assert first.id == second.id
    assert first.farmer_created is False
    assert first.source_module == "weather_to_action"
    assert (await service.list(user, pending_only=True))[0].id == first.id


@pytest.mark.asyncio
async def test_source_action_identity_isolated_by_farm(db_session):
    user, farm = await _owner(db_session)
    other_farm = Farm(user_id=user.id, name="Other", crop="paddy", status="active")
    db_session.add(other_farm)
    await db_session.flush()
    service = ActionVerificationService(db_session)
    source = SourceAction(
        source_feature="weather_to_action", source_record_id="daily:rain",
        source_version="1", action_code="Check drainage",
        suggestion_time=datetime.now(UTC), source_verified=False,
    )
    one = await service.register_source_action(user, farm.id, source)
    two = await service.register_source_action(user, other_farm.id, source)
    assert one.id != two.id


@pytest.mark.asyncio
async def test_non_actionable_or_expired_source_is_not_registered(db_session):
    user, farm = await _owner(db_session)
    service = ActionVerificationService(db_session)
    missing = SourceAction(
        source_feature="weather_to_action", source_record_id="missing", source_version="1",
        action_code="", suggestion_time=datetime.now(UTC), source_verified=False,
    )
    assert await service.register_source_action(user, farm.id, missing) is None
    expired = SourceAction(
        source_feature="weather_to_action", source_record_id="old", source_version="1",
        action_code="Old action", suggestion_time=datetime(2020, 1, 1, tzinfo=UTC),
        expires_at=datetime(2020, 1, 2, tzinfo=UTC), source_verified=False,
    )
    assert await service.register_source_action(user, farm.id, expired) is None


@pytest.mark.asyncio
async def test_expired_existing_action_is_not_in_pending_list(db_session):
    user, farm = await _owner(db_session)
    service = ActionVerificationService(db_session)
    action = await service.create(
        user,
        ActionCreateIn(
            farm_id=farm.id, source_feature="farmer_task", source_record_id="expired-1",
            source_version="1", action_code="Old task", farmer_created=True,
            source_verified=False, suggestion_time=datetime(2020, 1, 1, tzinfo=UTC),
            expires_at=datetime(2020, 1, 2, tzinfo=UTC),
        ),
    )
    assert action.id not in {row.id for row in await service.list(user, pending_only=True)}
