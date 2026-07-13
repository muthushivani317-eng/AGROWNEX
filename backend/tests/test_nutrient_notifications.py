"""The Nutrient ↔ Notification engine reuse: a confirmed deficiency surfaces as a
notification, and an inconclusive analysis surfaces a soil-test recommendation."""
from __future__ import annotations

import base64
from datetime import UTC, datetime

from app.modules.auth.models import User
from app.modules.disease.quality import QualityResult
from app.modules.disease.storage import MockStorage
from app.modules.farms.models import Farm, FarmLocation
from app.modules.notifications.service import NotificationService
from app.modules.nutrient import service as service_module
from app.modules.nutrient.parser import NutrientObservation
from app.modules.nutrient.schemas import AnalyzeNutrientRequest
from app.modules.nutrient.service import NutrientService
from app.modules.soil.models import SoilProfile

NOW = datetime(2026, 7, 12, 6, 0, tzinfo=UTC)


def _observation(primary: str | None) -> NutrientObservation:
    return NutrientObservation(
        plant_present=True,
        reject_reason=None,
        crop="paddy",
        visible_symptoms=["yellowing"],
        primary=primary,
        secondary=None,
        visual_confidence=68,
        severity="moderate",
        affected_area="widespread",
        explanation_tamil="ta",
        explanation_english="en",
    )


class FakeProvider:
    name = "gemini"
    model = "fake-nutrient"

    def __init__(self, primary: str | None) -> None:
        self._primary = primary

    async def analyze(self, request) -> NutrientObservation:
        return _observation(self._primary)


async def _user_farm(db_session, uid: str):
    user = User(firebase_uid=uid, status="active")
    db_session.add(user)
    await db_session.flush()
    farm = Farm(user_id=user.id, name="Field A")
    db_session.add(farm)
    await db_session.flush()
    farm.location = FarmLocation(farm_id=farm.id, latitude=10.7, longitude=79.1)
    await db_session.flush()
    return user, farm


def _request(farm_id) -> AnalyzeNutrientRequest:
    return AnalyzeNutrientRequest(
        image_base64=base64.b64encode(b"\x00" * 64).decode(),
        mime_type="image/jpeg",
        farm_id=farm_id,
    )


def _accept_quality(monkeypatch) -> None:
    monkeypatch.setattr(
        service_module, "assess_quality", lambda _m: QualityResult(True, [])
    )


async def test_confirmed_deficiency_creates_notification(db_session, monkeypatch) -> None:
    _accept_quality(monkeypatch)
    user, farm = await _user_farm(db_session, "fb-nutnotif-1")
    db_session.add(SoilProfile(user_id=user.id, farm_id=farm.id, nitrogen=200.0))
    await db_session.flush()

    service = NutrientService(
        db_session, provider=FakeProvider("nitrogen"), storage=MockStorage(), now=NOW
    )
    await service.analyze(user, _request(farm.id))

    notifications = NotificationService(db_session, now=NOW, enable_weather=False)
    await notifications.sync(user)
    page = await notifications.list_notifications(user, module="nutrient", sync=False)
    assert any(n.event_type == "deficiency_detected" for n in page.items)


async def test_inconclusive_analysis_recommends_a_test(db_session, monkeypatch) -> None:
    _accept_quality(monkeypatch)
    user, farm = await _user_farm(db_session, "fb-nutnotif-2")

    service = NutrientService(
        db_session, provider=FakeProvider(None), storage=MockStorage(), now=NOW
    )
    await service.analyze(user, _request(farm.id))

    notifications = NotificationService(db_session, now=NOW, enable_weather=False)
    await notifications.sync(user)
    page = await notifications.list_notifications(user, module="nutrient", sync=False)
    assert any(n.event_type == "test_recommended" for n in page.items)
