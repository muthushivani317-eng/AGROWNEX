import pytest
from app.modules.auth.models import User
from app.modules.farms.models import Farm
from app.modules.produce.harvest_readiness_registry import HarvestReadinessRegistry
from app.modules.produce.harvest_readiness_service import HarvestReadinessService


async def _owned(db_session):
    user = User(firebase_uid="harvest-owner", status="active")
    db_session.add(user)
    await db_session.flush()
    farm = Farm(user_id=user.id, name="Harvest field", crop="paddy")
    db_session.add(farm)
    await db_session.flush()
    return user, farm


async def test_empty_verified_registry_persists_safe_no_rule_result(db_session) -> None:
    user, farm = await _owned(db_session)
    service = HarvestReadinessService(
        db_session, registry=HarvestReadinessRegistry([])
    )

    result = await service.evaluate(
        user,
        farm_id=farm.id,
        crop_cycle_id="cycle-2026",
        observations=(),
        weather_freshness="missing",
        idempotency_key="harvest-evaluate-0001",
    )

    assert result.state == "no_verified_readiness_rule"
    assert result.criteria_version is None
    assert "harvest_date" not in result.evidence_snapshot
    assert (await service.current(user, farm.id, "cycle-2026")).id == result.id
    assert len(await service.history(user, result.id)) == 1


async def test_cross_user_cannot_read_harvest_readiness(db_session) -> None:
    user, farm = await _owned(db_session)
    other = User(firebase_uid="harvest-other", status="active")
    db_session.add(other)
    await db_session.flush()
    service = HarvestReadinessService(
        db_session, registry=HarvestReadinessRegistry([])
    )
    result = await service.evaluate(
        user,
        farm_id=farm.id,
        crop_cycle_id="cycle-private",
        observations=(),
        weather_freshness="missing",
        idempotency_key="harvest-evaluate-private",
    )

    with pytest.raises(PermissionError):
        await service.current(other, farm.id, "cycle-private")
    assert await service.history(other, result.id) == []
