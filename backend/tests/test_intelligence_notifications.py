"""The Crop Intelligence ↔ Notification engine reuse.

A high/critical overall farm-health risk surfaces as a notification; a low/medium risk
never does. Also unit-tests the pure ``collect_intelligence`` collector.
"""
from __future__ import annotations

from datetime import UTC, datetime

from app.modules.auth.models import User
from app.modules.disease.models import DiseaseReport
from app.modules.farms.models import Farm, FarmLocation
from app.modules.intelligence.service import IntelligenceService
from app.modules.notifications.collectors import (
    IntelligenceReportView,
    collect_intelligence,
)
from app.modules.notifications.service import NotificationService

NOW = datetime(2026, 7, 12, 6, 0, tzinfo=UTC)


async def _user_farm(db_session, uid: str):
    user = User(firebase_uid=uid, status="active")
    db_session.add(user)
    await db_session.flush()
    farm = Farm(user_id=user.id, name="Field A", crop="paddy")
    db_session.add(farm)
    await db_session.flush()
    farm.location = FarmLocation(farm_id=farm.id, latitude=10.7, longitude=79.1)
    await db_session.flush()
    return user, farm


async def _add_disease(db_session, user, farm, *, severity, confidence) -> None:
    db_session.add(
        DiseaseReport(
            user_id=user.id, farm_id=farm.id, image_url="https://r2/x.jpg",
            disease="Leaf blast", confidence=confidence, severity=severity, language="ta",
        )
    )
    await db_session.flush()


def _intel(db_session) -> IntelligenceService:
    return IntelligenceService(db_session, weather_service=None, now=NOW, enable_weather=False)


# --------------------------------------------------------------------------- #
# Pure collector
# --------------------------------------------------------------------------- #
class TestCollectIntelligence:
    def test_critical_risk_emits_event(self) -> None:
        events = collect_intelligence(
            IntelligenceReportView(report_id="r1", farm_id="f1", overall_risk="critical",
                                   overall_health_score=30)
        )
        assert len(events) == 1
        assert events[0].event_type == "critical_risk"
        assert events[0].module == "intelligence"

    def test_high_risk_emits_event(self) -> None:
        events = collect_intelligence(
            IntelligenceReportView(report_id="r1", farm_id="f1", overall_risk="high")
        )
        assert events[0].event_type == "high_risk"

    def test_low_and_medium_risk_are_silent(self) -> None:
        assert collect_intelligence(
            IntelligenceReportView(report_id="r1", farm_id="f1", overall_risk="low")
        ) == []
        assert collect_intelligence(
            IntelligenceReportView(report_id="r1", farm_id="f1", overall_risk="medium")
        ) == []


# --------------------------------------------------------------------------- #
# End-to-end through the Notification engine
# --------------------------------------------------------------------------- #
async def test_critical_risk_report_creates_notification(db_session) -> None:
    user, farm = await _user_farm(db_session, "fb-intelnotif-1")
    await _add_disease(db_session, user, farm, severity="high", confidence=92)
    report = await _intel(db_session).refresh(user, farm.id)
    assert report.overall_risk == "critical"

    notifications = NotificationService(db_session, now=NOW, enable_weather=False)
    await notifications.sync(user)
    page = await notifications.list_notifications(user, module="intelligence", sync=False)
    assert any(n.event_type == "critical_risk" for n in page.items)


async def test_healthy_report_creates_no_intelligence_notification(db_session) -> None:
    user, farm = await _user_farm(db_session, "fb-intelnotif-2")
    # No adverse module data → low risk → no alert.
    report = await _intel(db_session).refresh(user, farm.id)
    assert report.overall_risk == "low"

    notifications = NotificationService(db_session, now=NOW, enable_weather=False)
    await notifications.sync(user)
    page = await notifications.list_notifications(user, module="intelligence", sync=False)
    assert not any(n.event_type in ("critical_risk", "high_risk") for n in page.items)
