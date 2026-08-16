import pytest
from app.modules.auth.models import User
from app.modules.calendar.registry import CropStageRegistry
from app.modules.farms.models import Farm
from app.modules.growth.stage_service import StageConflictError, StageTrackingService
from app.modules.growth.stage_tracking import StageEvidence


async def setup_owned(db_session):
    user = User(firebase_uid="stage-owner", status="active")
    db_session.add(user)
    await db_session.flush()
    farm = Farm(user_id=user.id, name="Stage field")
    db_session.add(farm)
    await db_session.flush()
    return user, farm


async def test_idempotency_history_and_restart_persistence(db_session) -> None:
    user, farm = await setup_owned(db_session)
    service = StageTrackingService(db_session)
    args = dict(
        farm_id=farm.id,
        crop_cycle_id="cycle-2026",
        event="confirm",
        stage="seedling",
        expected_version=None,
        idempotency_key="stage-confirm-0001",
        evidence=StageEvidence(supports=["farmer_selection"]),
    )
    first = await service.apply(user, **args)
    duplicate = await service.apply(user, **args)
    assert duplicate.id == first.id
    assert duplicate.version == 1
    assert len(await service.history(user, first.id)) == 1
    restarted = StageTrackingService(db_session)
    assert (await restarted.current(user, farm.id, "cycle-2026")).confirmed_stage == "seedling"


async def test_stale_offline_update_requires_reconciliation(db_session) -> None:
    user, farm = await setup_owned(db_session)
    service = StageTrackingService(db_session)
    row = await service.apply(
        user,
        farm_id=farm.id,
        crop_cycle_id="cycle-2026",
        event="confirm",
        stage="seedling",
        expected_version=None,
        idempotency_key="stage-confirm-0002",
        evidence=StageEvidence(supports=["farmer_selection"]),
    )
    with pytest.raises(StageConflictError, match="STALE_STAGE_VERSION"):
        await service.apply(
            user,
            farm_id=farm.id,
            crop_cycle_id="cycle-2026",
            event="correct",
            stage="germination",
            expected_version=row.version - 1,
            idempotency_key="offline-correction-0001",
            evidence=StageEvidence(conflicts=["offline_edit"]),
        )


async def test_client_cannot_self_assert_a_verified_stage_registry(db_session) -> None:
    user, farm = await setup_owned(db_session)
    farm.crop = "paddy"
    service = StageTrackingService(db_session, stage_registry=CropStageRegistry([]))

    row = await service.apply(
        user,
        farm_id=farm.id,
        crop_cycle_id="cycle-unverified",
        event="evaluate",
        stage=None,
        expected_version=None,
        idempotency_key="stage-evaluate-unverified-1",
        evidence=StageEvidence(
            registry_verified=True,
            registry_version="forged-v1",
            planting_date_present=True,
            suggested_stage="flowering",
        ),
    )

    assert row.state == "stage_unknown"
    assert row.suggested_stage is None
    assert row.registry_version is None
    assert row.evidence_snapshot["missing"] == ["NO_VERIFIED_STAGE_MODEL"]
