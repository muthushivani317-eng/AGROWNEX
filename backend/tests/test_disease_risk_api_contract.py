import pytest
from app.main import app
from app.modules.auth.models import User
from app.modules.disease_risk.service import DiseaseRiskService
from app.modules.farms.models import Farm


def test_disease_risk_router_is_registered_with_required_workflow() -> None:
    paths = {route.path for route in app.routes}
    assert "/api/v1/disease-risk/evaluate" in paths
    assert "/api/v1/disease-risk/current" in paths
    assert "/api/v1/disease-risk/history" in paths
    assert "/api/v1/disease-risk/{risk_id}" in paths
    assert "/api/v1/disease-risk/{risk_id}/acknowledge" in paths


def test_no_rule_status_is_farmer_safe() -> None:
    from app.modules.disease_risk.schemas import RiskStatus

    assert RiskStatus.NO_VERIFIED_RULE_AVAILABLE.value == "NO_VERIFIED_RULE_AVAILABLE"


@pytest.mark.asyncio
async def test_no_verified_rule_is_persisted_idempotently_and_owner_scoped(db_session) -> None:
    owner = User(firebase_uid="risk-owner", status="active")
    other = User(firebase_uid="risk-other", status="active")
    db_session.add_all([owner, other])
    await db_session.flush()
    farm = Farm(user_id=owner.id, name="Risk field", crop="paddy")
    db_session.add(farm)
    await db_session.flush()
    service = DiseaseRiskService(db_session)
    first = await service.evaluate(owner, farm.id, None, "risk-evaluation-0001")
    duplicate = await service.evaluate(owner, farm.id, None, "risk-evaluation-0001")
    assert first.id == duplicate.id
    assert first.status == "NO_VERIFIED_RULE_AVAILABLE"
    assert first.risk_level is None
    assert first.notification_emitted is False
    assert (await service.current(owner, farm.id)).id == first.id
    items, total = await service.history(owner, farm.id, 20, 0)
    assert total == 1 and items[0].id == first.id
    with pytest.raises(PermissionError, match="FARM_NOT_OWNED"):
        await service.current(other, farm.id)
    with pytest.raises(LookupError, match="DISEASE_RISK_NOT_FOUND"):
        await service.get(other, first.id)
