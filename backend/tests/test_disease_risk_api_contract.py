import httpx
import pytest
from app.core.database import get_session
from app.main import app
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.disease_risk.models import DiseaseRiskAlert
from app.modules.disease_risk.service import DiseaseRiskService
from app.modules.farms.models import Farm, FarmLocation


def _app_for(db_session, user):
    async def session_override():
        yield db_session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_current_user] = lambda: user
    return app


def test_confidence_column_accepts_released_evidence_labels() -> None:
    column = DiseaseRiskAlert.__table__.c.confidence
    released_label = "sourced_public_reference_evidence"

    assert len(released_label) > 30
    assert column.type.length is not None
    assert column.type.length >= len(released_label)


def test_disease_risk_router_is_registered_with_required_workflow() -> None:
    paths = set(app.openapi()["paths"])
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
    # crop is "redgram", not "paddy": as of 2026-08-18 two real, cited rule
    # packs (paddy_sheath_blight, paddy_bacterial_leaf_blight -- see
    # app/modules/disease_risk/data/rule_packs/) are live for paddy, so a
    # paddy farm would no longer hit RULE_PACK_UNAVAILABLE here (it would hit
    # STAGE_UNCONFIRMED instead, since no stage is confirmed below). redgram
    # still has no rule pack, so this test's "no verified guidance available"
    # path stays accurate. This test is about the persisted
    # NO_VERIFIED_RULE_AVAILABLE behavior in general, not paddy specifically.
    farm = Farm(user_id=owner.id, name="Risk field", crop="redgram")
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


@pytest.mark.asyncio
async def test_tamil_nadu_district_resolves_state_scoped_paddy_rule(db_session) -> None:
    owner = User(firebase_uid="risk-tn-owner", status="active")
    db_session.add(owner)
    await db_session.flush()
    farm = Farm(user_id=owner.id, name="TN paddy field", crop="paddy")
    farm.location = FarmLocation(district="Thanjavur", source="manual")
    db_session.add(farm)
    await db_session.flush()

    result = await DiseaseRiskService(db_session).evaluate(
        owner, farm.id, None, "risk-tn-region-0001"
    )

    assert result.status != "NO_VERIFIED_RULE_AVAILABLE"
    assert result.rule_pack_id is not None
    assert result.rule_verification_status == "SOURCED_PUBLIC_REFERENCE"


@pytest.mark.asyncio
async def test_evaluate_route_matches_tamil_nadu_paddy_rule(db_session) -> None:
    owner = User(firebase_uid="risk-tn-route-owner", status="active")
    db_session.add(owner)
    await db_session.flush()
    farm = Farm(user_id=owner.id, name="TN route paddy field", crop="paddy")
    farm.location = FarmLocation(district="Thanjavur District", source="manual")
    db_session.add(farm)
    await db_session.flush()

    transport = httpx.ASGITransport(app=_app_for(db_session, owner))
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
        response = await client.post(
            "/api/v1/disease-risk/evaluate",
            json={"farm_id": str(farm.id), "idempotency_key": "route-risk-tn-0001"},
        )

    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["status"] != "NO_VERIFIED_RULE_AVAILABLE"
    assert payload["rule_verification_status"] == "SOURCED_PUBLIC_REFERENCE"
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_unknown_district_cannot_use_tamil_nadu_paddy_rule(db_session) -> None:
    owner = User(firebase_uid="risk-foreign-owner", status="active")
    db_session.add(owner)
    await db_session.flush()
    farm = Farm(user_id=owner.id, name="Foreign paddy field", crop="paddy")
    farm.location = FarmLocation(district="Mysuru", source="manual")
    db_session.add(farm)
    await db_session.flush()

    result = await DiseaseRiskService(db_session).evaluate(
        owner, farm.id, None, "risk-foreign-region-0001"
    )

    assert result.status == "NO_VERIFIED_RULE_AVAILABLE"
    assert result.rule_pack_id is None


@pytest.mark.asyncio
async def test_evaluate_route_saves_no_verified_rule_and_hides_foreign_farms(db_session) -> None:
    owner = User(firebase_uid="risk-route-owner", status="active")
    other = User(firebase_uid="risk-route-other", status="active")
    db_session.add_all([owner, other])
    await db_session.flush()
    farm = Farm(user_id=owner.id, name="Unsupported crop", crop="redgram")
    db_session.add(farm)
    await db_session.flush()

    transport = httpx.ASGITransport(app=_app_for(db_session, owner))
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
        response = await client.post(
            "/api/v1/disease-risk/evaluate",
            json={"farm_id": str(farm.id), "idempotency_key": "route-risk-0001"},
        )
    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["status"] == "NO_VERIFIED_RULE_AVAILABLE"
    assert payload["risk_level"] is None

    app.dependency_overrides[get_current_user] = lambda: other
    foreign_transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=foreign_transport, base_url="http://localhost"
    ) as client:
        denied = await client.post(
            "/api/v1/disease-risk/evaluate",
            json={"farm_id": str(farm.id), "idempotency_key": "route-risk-0002"},
        )
    assert denied.status_code == 404
    assert denied.json()["error_code"] == "FARM_NOT_OWNED"
    app.dependency_overrides.clear()
