from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest
from app.modules.action_verification.schemas import ActionCreateIn
from app.modules.action_verification.service import ActionVerificationService
from app.modules.auth.models import User
from app.modules.farms.exceptions import FarmNotFoundError
from app.modules.farms.models import Farm
from app.modules.organic.governance import canonical_input_hash
from app.modules.organic.models import OrganicInput
from app.modules.organic_advisory.exceptions import OrganicAdvisoryNotAllowedError
from app.modules.organic_advisory.schemas import (
    SatelliteFindingIn,
    SatelliteScoutingIn,
    TrustedWeatherGateIn,
    WeatherOrganicGateIn,
)
from app.modules.organic_advisory.service import OrganicAdvisoryService
from app.modules.satellite.models import SatelliteAlert, SatelliteSession
from app.modules.weather.schemas import WeatherInsight


class _TrustedWeather:
    def __init__(self, *, fetched_at=None):
        self.fetched_at = fetched_at or datetime.now(UTC)

    async def get_by_farm(self, user, farm_id):
        del user, farm_id
        insight = WeatherInsight(
            code="spraying.avoid_rain",
            category="spraying",
            severity="warning",
            title="Rain",
            message="Postpone",
            params={},
        )
        data = {
            "fetched_at": self.fetched_at.isoformat(),
            "source": "open-meteo",
            "data_state": "live",
            "insights": [insight.model_dump()],
            "hourly": [],
        }
        safe = SimpleNamespace(
            time=(datetime.now(UTC) + timedelta(hours=3)).isoformat(),
            precipitation_probability_pct=10,
            precipitation_mm=0,
            wind_speed_kmh=5,
        )

        class Bundle:
            fetched_at = data["fetched_at"]
            source = data["source"]
            data_state = data["data_state"]
            insights = [insight]
            hourly = [safe]

            def model_dump(self, **kwargs):
                del kwargs
                return data

        return Bundle()


async def _owner(db_session):
    user = User(firebase_uid="organic-advisory-owner", status="active")
    db_session.add(user)
    await db_session.flush()
    farm = Farm(user_id=user.id, name="Advisory farm", crop="paddy", status="active")
    db_session.add(farm)
    await db_session.flush()
    return user, farm


async def _approved_input(db_session, *, gates):
    item = OrganicInput(
        slug=f"neem-{len(gates)}",
        category="botanical",
        name_en="Neem",
        name_ta="Neem",
        purpose_en="Approved purpose",
        purpose_ta="Approved purpose",
        guidance={},
        applicable_crops=["paddy"],
        applicable_stages=[],
        applicable_regions=[],
        limitations={"weather_gates": gates},
        source_organization="TNAU",
        document_reference="guide-1",
        source_url="https://example.test/guide",
        source_version="2026-1",
        content_hash="pending",
        review_status="approved",
        reviewed_at=datetime.now(UTC),
        effective_from=date.today(),
    )
    item.content_hash = canonical_input_hash(item)
    db_session.add(item)
    await db_session.flush()
    return item


@pytest.mark.asyncio
async def test_weather_only_gates_allowlisted_approved_action(db_session):
    user, farm = await _owner(db_session)
    item = await _approved_input(db_session, gates=["spraying.avoid_rain"])
    original = await ActionVerificationService(db_session).create(
        user,
        ActionCreateIn(
            farm_id=farm.id,
            source_feature="organic_calendar",
            source_record_id="task-1",
            source_version="1",
            action_code="apply_neem",
            suggestion_time=datetime.now(UTC),
        ),
    )
    now = datetime.now(UTC)
    payload = WeatherOrganicGateIn(
        farm_id=farm.id,
        action_workflow_id=original.id,
        organic_input_id=item.id,
        signal_code="spraying.avoid_rain",
        forecast_observed_at=now,
        safe_after=now + timedelta(hours=4),
        forecast_valid_until=now + timedelta(hours=12),
        forecast_source="open-meteo",
        forecast_version="forecast-1",
    )
    first = await OrganicAdvisoryService(db_session).weather_gate(user, payload)
    second = await OrganicAdvisoryService(db_session).weather_gate(user, payload)
    assert first.gate_action.id == second.gate_action.id
    assert first.decision == "postpone"
    assert first.gate_action.action_code == "postpone_organic_application_for_rain"
    assert first.gate_action.source_verified is False


@pytest.mark.asyncio
async def test_trusted_weather_persists_provenance_history_and_one_intent(db_session):
    user, farm = await _owner(db_session)
    item = await _approved_input(db_session, gates=["spraying.avoid_rain"])
    original = await ActionVerificationService(db_session).create(
        user,
        ActionCreateIn(
            farm_id=farm.id,
            source_feature="organic_calendar",
            source_record_id="trusted-weather-task",
            source_version="1",
            action_code="apply_neem",
            suggestion_time=datetime.now(UTC),
        ),
    )
    payload = TrustedWeatherGateIn(
        farm_id=farm.id,
        action_workflow_id=original.id,
        organic_input_id=item.id,
        idempotency_key="trusted-weather-001",
    )
    service = OrganicAdvisoryService(db_session, weather=_TrustedWeather())
    first = await service.trusted_weather_gate(user, payload)
    second = await service.trusted_weather_gate(user, payload)

    assert first.reschedule_id == second.reschedule_id
    assert first.notification_intent_id == second.notification_intent_id
    assert first.source_verified is True
    assert first.signal_code == "spraying.avoid_rain"
    assert original.due_at == first.rescheduled_for

    other = await _approved_input(db_session, gates=["spraying.avoid_rain", "spraying.avoid_wind"])
    with pytest.raises(ValueError, match="IDEMPOTENCY_CONFLICT"):
        await service.trusted_weather_gate(
            user,
            payload.model_copy(
                update={
                    "organic_input_id": other.id,
                }
            ),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["farmer_reported_done", "cancelled", "skipped"])
async def test_trusted_weather_rejects_non_actionable_workflow(db_session, status):
    user, farm = await _owner(db_session)
    item = await _approved_input(db_session, gates=["spraying.avoid_rain"])
    original = await ActionVerificationService(db_session).create(
        user,
        ActionCreateIn(
            farm_id=farm.id,
            source_feature="organic_calendar",
            source_record_id=f"non-actionable-{status}",
            source_version="1",
            action_code="apply_neem",
            suggestion_time=datetime.now(UTC),
        ),
    )
    original.status = status
    await db_session.flush()
    with pytest.raises(OrganicAdvisoryNotAllowedError):
        await OrganicAdvisoryService(db_session, weather=_TrustedWeather()).trusted_weather_gate(
            user,
            TrustedWeatherGateIn(
                farm_id=farm.id,
                action_workflow_id=original.id,
                organic_input_id=item.id,
                idempotency_key=f"non-actionable-{status}",
            ),
        )


@pytest.mark.asyncio
async def test_trusted_weather_rejects_stale_provider_snapshot(db_session):
    user, farm = await _owner(db_session)
    item = await _approved_input(db_session, gates=["spraying.avoid_rain"])
    original = await ActionVerificationService(db_session).create(
        user,
        ActionCreateIn(
            farm_id=farm.id,
            source_feature="organic_calendar",
            source_record_id="stale-weather-task",
            source_version="1",
            action_code="apply_neem",
            suggestion_time=datetime.now(UTC),
        ),
    )
    service = OrganicAdvisoryService(
        db_session, weather=_TrustedWeather(fetched_at=datetime.now(UTC) - timedelta(hours=3))
    )
    with pytest.raises(OrganicAdvisoryNotAllowedError):
        await service.trusted_weather_gate(
            user,
            TrustedWeatherGateIn(
                farm_id=farm.id,
                action_workflow_id=original.id,
                organic_input_id=item.id,
                idempotency_key="stale-weather-001",
            ),
        )


@pytest.mark.asyncio
async def test_weather_metrics_are_owner_scoped_aggregates(db_session):
    user, farm = await _owner(db_session)
    other = User(firebase_uid="organic-metrics-other", status="active")
    db_session.add(other)
    await db_session.flush()
    service = OrganicAdvisoryService(db_session)

    metrics = await service.weather_metrics(user, farm.id)
    assert metrics == {
        "farm_id": farm.id,
        "snapshot_count": 0,
        "reschedule_count": 0,
        "pending_notification_intents": 0,
    }
    with pytest.raises(FarmNotFoundError):
        await service.weather_metrics(other, farm.id)


@pytest.mark.asyncio
async def test_weather_cannot_invent_gate_missing_from_catalogue(db_session):
    user, farm = await _owner(db_session)
    item = await _approved_input(db_session, gates=[])
    original = await ActionVerificationService(db_session).create(
        user,
        ActionCreateIn(
            farm_id=farm.id,
            source_feature="organic_calendar",
            source_record_id="task-2",
            source_version="1",
            action_code="apply_neem",
            suggestion_time=datetime.now(UTC),
        ),
    )
    now = datetime.now(UTC)
    with pytest.raises(OrganicAdvisoryNotAllowedError):
        await OrganicAdvisoryService(db_session).weather_gate(
            user,
            WeatherOrganicGateIn(
                farm_id=farm.id,
                action_workflow_id=original.id,
                organic_input_id=item.id,
                signal_code="spraying.avoid_wind",
                forecast_observed_at=now,
                safe_after=now + timedelta(hours=2),
                forecast_valid_until=now + timedelta(hours=8),
                forecast_source="open-meteo",
                forecast_version="forecast-2",
            ),
        )


@pytest.mark.asyncio
async def test_weather_cannot_gate_non_organic_action(db_session):
    user, farm = await _owner(db_session)
    item = await _approved_input(db_session, gates=["spraying.avoid_rain"])
    original = await ActionVerificationService(db_session).create(
        user,
        ActionCreateIn(
            farm_id=farm.id,
            source_feature="farmer_task",
            source_record_id="task-3",
            source_version="1",
            action_code="generic_spray",
            suggestion_time=datetime.now(UTC),
        ),
    )
    now = datetime.now(UTC)
    with pytest.raises(OrganicAdvisoryNotAllowedError):
        await OrganicAdvisoryService(db_session).weather_gate(
            user,
            WeatherOrganicGateIn(
                farm_id=farm.id,
                action_workflow_id=original.id,
                organic_input_id=item.id,
                signal_code="spraying.avoid_rain",
                forecast_observed_at=now,
                safe_after=now + timedelta(hours=2),
                forecast_valid_until=now + timedelta(hours=8),
                forecast_source="open-meteo",
                forecast_version="forecast-3",
            ),
        )


@pytest.mark.asyncio
async def test_satellite_alert_creates_idempotent_non_diagnostic_scouting(db_session):
    user, farm = await _owner(db_session)
    scene = SatelliteSession(
        user_id=user.id,
        farm_id=farm.id,
        provider="sentinel",
        status="available",
        unavailable_reason="none",
        is_sample=False,
        capture_date=date.today(),
        cloud_cover=10,
        confidence=80,
        session_metadata={"scene_id": "S2-scene-123"},
    )
    db_session.add(scene)
    await db_session.flush()
    alert = SatelliteAlert(
        user_id=user.id,
        farm_id=farm.id,
        session_id=scene.id,
        code="vegetation.decline",
        category="vegetation",
        severity="warning",
        priority="high",
    )
    db_session.add(alert)
    await db_session.flush()
    payload = SatelliteScoutingIn(
        farm_id=farm.id,
        satellite_alert_id=alert.id,
        expires_at=datetime.now(UTC) + timedelta(days=2),
    )
    first = await OrganicAdvisoryService(db_session).satellite_scouting(user, payload)
    second = await OrganicAdvisoryService(db_session).satellite_scouting(user, payload)
    assert first.action.id == second.action.id
    assert first.action.action_code == "field_scouting_vegetation"
    assert first.action.source_verified is False
    assert "does not diagnose" in first.limitation
    assert first.scene_id == "S2-scene-123"

    findings = SatelliteFindingIn(
        observations=["weed_pressure"], idempotency_key="finding-event-0001"
    )
    recorded = await OrganicAdvisoryService(db_session).record_satellite_findings(
        user, first.action.id, findings
    )
    duplicate = await OrganicAdvisoryService(db_session).record_satellite_findings(
        user, first.action.id, findings
    )
    assert recorded.log_entry_id == duplicate.log_entry_id
    assert recorded.follow_up_action.id == duplicate.follow_up_action.id
    assert recorded.diagnosis is None


@pytest.mark.asyncio
async def test_satellite_findings_accept_schema_boundaries_and_require_active_scouting(db_session):
    user, farm = await _owner(db_session)
    action = await ActionVerificationService(db_session).create(
        user,
        ActionCreateIn(
            farm_id=farm.id,
            source_feature="satellite_field_scouting",
            source_record_id="boundary-scene",
            source_version="1",
            action_code="field_scouting_variation",
            suggestion_time=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=1),
        ),
    )
    payload = SatelliteFindingIn(
        observations=[
            "visible_pest_or_disease_symptoms",
            "visible_nutrient_symptoms",
            "weed_pressure",
            "dry_soil",
            "waterlogging",
            "mulch_gap",
            "uneven_amendment",
            "physical_damage",
        ],
        idempotency_key="x" * 100,
    )
    recorded = await OrganicAdvisoryService(db_session).record_satellite_findings(
        user, action.id, payload
    )
    assert recorded.log_entry_id is not None
    action.status = "farmer_reported_done"
    await db_session.flush()
    with pytest.raises(OrganicAdvisoryNotAllowedError):
        await OrganicAdvisoryService(db_session).record_satellite_findings(
            user,
            action.id,
            SatelliteFindingIn(
                observations=["weed_pressure"], idempotency_key="inactive-finding-1"
            ),
        )


@pytest.mark.asyncio
async def test_unavailable_satellite_scene_cannot_create_scouting(db_session):
    user, farm = await _owner(db_session)
    scene = SatelliteSession(
        user_id=user.id,
        farm_id=farm.id,
        provider="sentinel",
        status="unavailable",
        unavailable_reason="cloud_cover",
        is_sample=False,
        capture_date=None,
        cloud_cover=90,
        confidence=0,
    )
    db_session.add(scene)
    await db_session.flush()
    alert = SatelliteAlert(
        user_id=user.id,
        farm_id=farm.id,
        session_id=scene.id,
        code="imagery.unavailable",
        category="imagery",
        severity="info",
        priority="low",
    )
    db_session.add(alert)
    await db_session.flush()
    with pytest.raises(OrganicAdvisoryNotAllowedError):
        await OrganicAdvisoryService(db_session).satellite_scouting(
            user,
            SatelliteScoutingIn(
                farm_id=farm.id,
                satellite_alert_id=alert.id,
                expires_at=datetime.now(UTC) + timedelta(days=1),
            ),
        )
