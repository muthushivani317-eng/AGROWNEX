from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.modules.admin.metrics import AdminMetrics
from app.modules.intelligence.schemas import IntelligenceReportOut
from app.modules.intelligence.sources import IntelligenceSources
from app.modules.memory.schemas import MemoryOut
from app.modules.memory.sources import MemorySources
from app.modules.notifications.service import NotificationService
from app.modules.notifications.sources import NotificationSources
from app.modules.nutrient.models import NutrientAnalysis, NutrientReport
from app.modules.nutrient.repository import NutrientRepository
from app.modules.nutrient.safety import consumer_safe_nutrient_finding
from app.modules.nutrient.service import NutrientService


def _raw_report(crop: str = "Groundnut"):
    analysis = SimpleNamespace(
        primary_deficiency="nitrogen",
        status="confirmed",
        confidence=97,
        severity="severe",
        needs_test=False,
        needs_expert=False,
    )
    recommendations = [
        SimpleNamespace(category="nutrient", code="nutrient.rec.nitrogen.deficiency"),
        SimpleNamespace(category="test", code="nutrient.rec.test.soil_test"),
        SimpleNamespace(category="expert", code="nutrient.rec.expert.consult"),
    ]
    return SimpleNamespace(
        id=uuid4(),
        farm_id=uuid4(),
        crop=crop,
        analysis=analysis,
        recommendations=recommendations,
        created_at=datetime.now(UTC),
        capture_date=None,
    )


def test_shared_consumer_view_preserves_raw_evidence_and_other_crops() -> None:
    groundnut = consumer_safe_nutrient_finding(
        crop="Groundnut",
        primary_deficiency="nitrogen",
        status="confirmed",
        confidence=97,
        needs_test=False,
    )
    assert groundnut.primary_deficiency is None
    assert groundnut.status == "not_confirmed"
    assert groundnut.confidence is None
    assert groundnut.needs_test is True
    assert groundnut.needs_expert is True
    assert groundnut.groundnut_specific_restricted is True

    paddy = consumer_safe_nutrient_finding(
        crop="Paddy",
        primary_deficiency="nitrogen",
        status="confirmed",
        confidence=97,
        needs_test=False,
    )
    assert paddy.status == "confirmed"
    assert paddy.confidence == 97
    assert paddy.groundnut_specific_restricted is False


@pytest.mark.asyncio
async def test_notification_memory_and_intelligence_use_safe_boundary(monkeypatch) -> None:
    report = _raw_report()

    async def recent_reports(_repo, _user_id, *, limit):
        return [report]

    async def list_reports(_repo, _user_id, _farm_id, *, limit, offset):
        return [report], 1

    async def latest_report(_repo, _user_id, _farm_id):
        return report

    monkeypatch.setattr(NutrientRepository, "recent_reports", recent_reports)
    monkeypatch.setattr(NutrientRepository, "list_reports", list_reports)
    monkeypatch.setattr(NutrientRepository, "latest_report", latest_report)

    user = SimpleNamespace(id=uuid4())
    farm = SimpleNamespace(id=report.farm_id, crop="Groundnut")
    now = datetime.now(UTC)

    events = await NotificationSources(object(), now=now)._collect_nutrient(user)
    assert [event.event_type for event in events] == ["test_recommended"]
    assert "nutrient" not in events[0].payload

    memories = await MemorySources(object(), now=now)._read_nutrient(user, farm)
    assert memories == []

    signal = await IntelligenceSources(object(), now=now)._read_nutrient(user, farm)
    assert signal is not None
    assert signal.primary is None
    assert signal.status == "not_confirmed"
    assert signal.confidence is None
    assert signal.needs_test is True

    # Consumer reads never overwrite the persisted/raw audit object.
    assert report.analysis.status == "confirmed"
    assert report.analysis.confidence == 97


@pytest.mark.asyncio
async def test_direct_service_recommendations_cannot_return_groundnut_remedies() -> None:
    report = _raw_report()
    service = object.__new__(NutrientService)

    async def require_farm(_user, _farm_id):
        return SimpleNamespace(id=_farm_id, crop="Groundnut")

    async def latest_report(_user_id, _farm_id):
        return report

    service._require_farm = require_farm
    service.repo = SimpleNamespace(latest_report=latest_report)
    recs = await service.recommendations(
        SimpleNamespace(id=uuid4()), report.farm_id
    )
    assert [rec.category for rec in recs] == ["test", "expert"]


@pytest.mark.asyncio
async def test_admin_metrics_exclude_unvalidated_groundnut_confidence_and_labels(
    db_session,
) -> None:
    user_id, farm_id = uuid4(), uuid4()
    groundnut = NutrientReport(
        user_id=user_id,
        farm_id=farm_id,
        crop="Groundnut",
        image_url="private://groundnut.jpg",
        provider="gemini",
        status="analyzed",
        language="en",
    )
    paddy = NutrientReport(
        user_id=user_id,
        farm_id=farm_id,
        crop="Paddy",
        image_url="private://paddy.jpg",
        provider="gemini",
        status="analyzed",
        language="en",
    )
    db_session.add_all([groundnut, paddy])
    await db_session.flush()
    db_session.add_all(
        [
            NutrientAnalysis(
                report_id=groundnut.id,
                primary_deficiency="nitrogen",
                status="confirmed",
                confidence=99,
                severity="severe",
                needs_test=False,
                needs_expert=False,
            ),
            NutrientAnalysis(
                report_id=paddy.id,
                primary_deficiency="potassium",
                status="confirmed",
                confidence=70,
                severity="moderate",
                needs_test=False,
                needs_expert=False,
            ),
        ]
    )
    await db_session.flush()

    metrics = AdminMetrics(db_session)
    assert await metrics._avg_confidence() == 70
    assert await metrics._nutrient_distribution() == [
        {"label": "potassium", "count": 1}
    ]


def test_legacy_groundnut_memory_and_intelligence_are_sanitized_on_read() -> None:
    now, farm_id = datetime.now(UTC), uuid4()
    memory = SimpleNamespace(
        id=uuid4(), farm_id=farm_id, source_module="nutrient",
        event_type="nutrient_deficiency_detected",
        summary="memory.event.nutrient_deficiency_detected",
        params={"nutrient": "nitrogen", "status": "confirmed"}, confidence=98,
        importance="high", importance_score=90, observation="inferred",
        season=None, season_year=None, crop="Groundnut", location=None,
        occurred_at=now, created_at=now, tags=[SimpleNamespace(tag="nitrogen")],
        events=[object()],
    )
    out = MemoryOut.from_memory(memory)
    assert out.summary == "memory.event.nutrient_review_required"
    assert out.params == {}
    assert out.confidence is None
    assert "nitrogen" not in out.tags

    report = SimpleNamespace(
        id=uuid4(), farm_id=farm_id, crop="Groundnut", generated_at=now,
        overall_health_score=60, confidence=88, overall_risk="high",
        sources_used=["nutrient", "weather"], created_at=now,
        health=SimpleNamespace(overall_health_score=60, confidence=88,
            disease_score=None, nutrient_score=20, soil_score=None,
            satellite_score=None, weather_score=80, growth_score=None),
        risk=SimpleNamespace(risk_score=65, priority_issues=[
            {"code": "nutrient_deficiency", "severity": "high", "modules": ["nutrient"]},
            {"code": "heat", "severity": "medium", "modules": ["weather"]},
        ]),
        recommendations=[
            SimpleNamespace(code="address_nitrogen", priority="high", category="nutrient", modules=["nutrient"], rank=1),
            SimpleNamespace(code="irrigate", priority="medium", category="weather", modules=["weather"], rank=2),
        ],
    )
    intelligence = IntelligenceReportOut.from_report(report)
    assert intelligence.health is not None
    assert intelligence.health.nutrient_score is None
    assert [item.code for item in intelligence.priority_issues] == ["heat"]
    assert [item.code for item in intelligence.recommendations] == ["irrigate"]
    assert intelligence.overall_health_score is None
    assert intelligence.health.overall_health_score is None
    assert intelligence.risk_score is None


@pytest.mark.asyncio
async def test_legacy_groundnut_notification_is_sanitized_without_mutation(monkeypatch) -> None:
    report_id, user_id, now = uuid4(), uuid4(), datetime.now(UTC)
    notification = SimpleNamespace(
        id=uuid4(), module="nutrient", event_type="deficiency_detected",
        farm_id=uuid4(), title_key="unsafe.title", message_key="unsafe.message",
        payload_json={"report_id": str(report_id), "farm_id": "farm", "nutrient": "nitrogen"},
        severity="warning", priority="high", action_route=None, read=False,
        created_at=now, scheduled_for=None, expires_at=None,
    )

    async def get_report(_repo, queried_id, queried_user):
        assert queried_id == report_id
        assert queried_user == user_id
        return SimpleNamespace(crop="Groundnut")

    monkeypatch.setattr(NutrientRepository, "get_report", get_report)
    service = object.__new__(NotificationService)
    service.session = object()
    out = await service.notification_out(SimpleNamespace(id=user_id), notification)
    assert out.event_type == "test_recommended"
    assert "nutrient" not in out.payload
    assert notification.event_type == "deficiency_detected"
    assert notification.payload_json["nutrient"] == "nitrogen"

    delivered = []

    async def deliver(request, *, channels):
        delivered.append(request)
        return []

    async def get_preferences(_user_id):
        return SimpleNamespace(in_app_enabled=True, push_enabled=False)

    async def add_delivery(_row):
        raise AssertionError("no delivery rows expected from empty provider result")

    service.repo = SimpleNamespace(
        get_preferences=get_preferences,
        add_delivery=add_delivery,
    )
    service.provider = SimpleNamespace(name="mock", deliver=deliver)
    await service._deliver(SimpleNamespace(id=user_id), notification, now)
    assert delivered[0].event_type == "test_recommended"
    assert "nutrient" not in delivered[0].payload


@pytest.mark.parametrize(
    ("case", "payload"),
    [
        ("missing", {"nutrient": "nitrogen", "status": "confirmed"}),
        ("invalid", {"report_id": "not-a-uuid", "nutrient": "nitrogen"}),
        ("deleted", {"report_id": str(uuid4()), "nutrient": "nitrogen"}),
        ("cross-user", {"report_id": str(uuid4()), "nutrient": "nitrogen"}),
    ],
)
@pytest.mark.asyncio
async def test_unverifiable_legacy_notifications_fail_closed(
    monkeypatch, case, payload
) -> None:
    now = datetime.now(UTC)
    notification = SimpleNamespace(
        id=uuid4(), module="nutrient", event_type="deficiency_detected",
        farm_id=uuid4(), title_key="unsafe.nitrogen.title",
        message_key="unsafe.confirmed.message",
        payload_json={**payload, "confidence": 99, "fertilizer": "unsafe"},
        severity="warning", priority="high", action_route=None, read=False,
        created_at=now, scheduled_for=None, expires_at=None,
    )

    async def get_report(_repo, _report_id, _user_id):
        assert case in {"deleted", "cross-user"}
        return None

    monkeypatch.setattr(NutrientRepository, "get_report", get_report)
    service = object.__new__(NotificationService)
    service.session = object()
    out = await service.notification_out(SimpleNamespace(id=uuid4()), notification)

    assert out.event_type == "test_recommended"
    assert out.title_key == "notifications.nutrient.test_recommended.title"
    assert out.message_key == "notifications.nutrient.test_recommended.message"
    assert set(out.payload) <= {"report_id", "farm_id"}
    assert notification.payload_json["nutrient"] == "nitrogen"
    assert notification.payload_json["confidence"] == 99


@pytest.mark.asyncio
async def test_verified_other_crop_legacy_notification_is_preserved(monkeypatch) -> None:
    report_id, now = uuid4(), datetime.now(UTC)
    notification = SimpleNamespace(
        id=uuid4(), module="nutrient", event_type="deficiency_detected",
        farm_id=uuid4(), title_key="original.title", message_key="original.message",
        payload_json={"report_id": str(report_id), "nutrient": "potassium"},
        severity="warning", priority="high", action_route=None, read=False,
        created_at=now, scheduled_for=None, expires_at=None,
    )

    async def get_report(_repo, _report_id, _user_id):
        return SimpleNamespace(crop="Paddy")

    monkeypatch.setattr(NutrientRepository, "get_report", get_report)
    service = object.__new__(NotificationService)
    service.session = object()
    out = await service.notification_out(SimpleNamespace(id=uuid4()), notification)
    assert out.event_type == "deficiency_detected"
    assert out.title_key == "original.title"
    assert out.payload["nutrient"] == "potassium"


@pytest.mark.asyncio
async def test_unverifiable_queued_push_delivery_uses_neutral_payload(monkeypatch) -> None:
    now, user_id = datetime.now(UTC), uuid4()
    notification = SimpleNamespace(
        id=uuid4(), module="nutrient", event_type="deficiency_detected",
        farm_id=uuid4(), title_key="unsafe.title", message_key="unsafe.message",
        payload_json={"nutrient": "nitrogen", "status": "confirmed", "confidence": 98},
        severity="warning", priority="high", action_route=None, read=False,
        created_at=now, scheduled_for=now, expires_at=None,
    )
    captured = []

    async def deliver(request, *, channels):
        captured.append((request, channels))
        return []

    async def get_preferences(_user_id):
        return SimpleNamespace(in_app_enabled=True, push_enabled=True)

    service = object.__new__(NotificationService)
    service.session = object()
    service.repo = SimpleNamespace(get_preferences=get_preferences)
    service.provider = SimpleNamespace(name="fcm", deliver=deliver)
    await service._deliver(SimpleNamespace(id=user_id), notification, now)

    request, channels = captured[0]
    assert channels == ("in_app", "push")
    assert request.event_type == "test_recommended"
    assert request.payload == {}
    assert notification.payload_json["nutrient"] == "nitrogen"


def test_groundnut_legacy_history_does_not_expose_unverified_aggregates():
    from app.modules.intelligence.schemas import IntelligenceHistoryOut

    now = datetime.now(UTC)
    history = SimpleNamespace(
        id=uuid4(),
        farm_id=uuid4(),
        report_id=uuid4(),
        overall_health_score=60,
        overall_risk="high",
        confidence=88,
        recorded_at=now,
        _sufficient_evidence=False,
    )

    result = IntelligenceHistoryOut.from_history(history)

    assert result.overall_health_score is None
    assert result.overall_risk == "unknown"
    assert result.confidence is None

def test_groundnut_mixed_legacy_sources_do_not_expose_aggregate():
    from app.modules.intelligence.schemas import IntelligenceReportOut

    now = datetime.now(UTC)
    report = SimpleNamespace(
        id=uuid4(),
        farm_id=uuid4(),
        crop="Groundnut",
        generated_at=now,
        created_at=now,
        overall_health_score=60,
        confidence=88,
        overall_risk="high",
        sources_used=["nutrient", "weather", "disease"],
        health=SimpleNamespace(
            overall_health_score=60,
            confidence=88,
            disease_score=75,
            nutrient_score=20,
            soil_score=None,
            satellite_score=None,
            weather_score=80,
            growth_score=None,
        ),
        risk=SimpleNamespace(risk_score=65, priority_issues=[]),
        recommendations=[],
    )

    result = IntelligenceReportOut.from_report(report)

    assert result.overall_health_score is None
    assert result.health.overall_health_score is None
    assert result.risk_score is None
    assert result.overall_risk == "unknown"
    assert result.confidence is None
