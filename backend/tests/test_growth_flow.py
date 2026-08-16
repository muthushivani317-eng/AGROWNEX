"""Integration tests for the growth service (fake analyzer + mock storage)."""
from __future__ import annotations

import base64
import uuid

import pytest
from app.modules.auth.models import User
from app.modules.disease.quality import QualityResult
from app.modules.disease.storage import MockStorage
from app.modules.farms.models import Farm, FarmLocation
from app.modules.growth import service as service_module
from app.modules.growth.analyzer import GrowthAnalysis
from app.modules.growth.constants import GrowthStage, PlantVigor
from app.modules.growth.exceptions import (
    FarmNotFoundError,
    GrowthImageNotFoundError,
    GrowthSessionNotFoundError,
    NoPlantDetectedError,
    PoorImageQualityError,
)
from app.modules.growth.schemas import UploadGrowthRequest
from app.modules.growth.service import GrowthService
from app.modules.ai.models import TokenUsage
from sqlalchemy import select


def make_analysis(
    *,
    plant: bool = True,
    reject: str | None = None,
    health: int = 78,
    stage: str = GrowthStage.VEGETATIVE.value,
    abnormalities: list[str] | None = None,
    needs_review: bool = False,
) -> GrowthAnalysis:
    return GrowthAnalysis(
        plant_present=plant,
        reject_reason=reject,
        growth_stage=stage,
        plant_vigor=PlantVigor.GOOD.value,
        health_score=health,
        confidence=72,
        leaf_color_observations=["green"],
        visible_abnormalities=abnormalities or [],
        changes_from_previous=[],
        recommendations=["irrigate"],
        needs_expert_review=needs_review,
        growth_summary_tamil="வளர்ச்சி நன்று",
        growth_summary_english="growing well",
        model_used="fake-growth",
        raw={"source": "fake"},
    )


class FakeProvider:
    model = "fake-growth"

    def __init__(self, analysis: GrowthAnalysis) -> None:
        self.analysis = analysis
        self.calls = 0
        self.last_request = None

    async def analyze(self, request) -> GrowthAnalysis:
        self.calls += 1
        self.last_request = request
        return self.analysis


def _b64(nbytes: int) -> str:
    return base64.b64encode(b"\x00" * nbytes).decode()


def _accept_quality(monkeypatch) -> None:
    monkeypatch.setattr(
        service_module, "assess_quality", lambda _m: QualityResult(True, [])
    )


async def _make_user(db_session, uid: str = "fb-growth-1") -> User:
    user = User(firebase_uid=uid, status="active")
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_farm(db_session, user: User, *, crop: str = "paddy") -> Farm:
    farm = Farm(user_id=user.id, name="North Field", crop=crop, crop_variety="ADT-43")
    db_session.add(farm)
    await db_session.flush()
    db_session.add(
        FarmLocation(farm_id=farm.id, latitude=9.9, longitude=78.1, source="gps")
    )
    await db_session.flush()
    return farm


def _service(db_session, provider, **kwargs) -> GrowthService:
    return GrowthService(
        db_session, provider=provider, storage=MockStorage(), **kwargs
    )


def _req(farm_id, **kwargs) -> UploadGrowthRequest:
    base = dict(image_base64=_b64(64), mime_type="image/jpeg", farm_id=farm_id)
    base.update(kwargs)
    return UploadGrowthRequest(**base)


async def test_upload_creates_session_image_analysis_timeline(
    db_session, session_factory, monkeypatch
):
    monkeypatch.setattr("app.modules.ai.usage_ledger.SessionLocal", session_factory)
    _accept_quality(monkeypatch)
    provider = FakeProvider(make_analysis())
    service = _service(db_session, provider)
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)

    outcome = await service.upload(user, _req(farm.id))
    assert provider.calls == 1
    assert outcome.image.image_url.startswith("https://r2.mock.local/growth/")
    assert outcome.analysis.growth_stage == "vegetative"
    assert outcome.analysis.growth_summary_tamil == "வளர்ச்சி நன்று"
    assert outcome.timeline_entry.week_number == 1
    assert outcome.timeline_entry.health_delta is None  # first entry
    # Session rolled up.
    assert outcome.session.image_count == 1
    assert outcome.session.current_growth_stage == "vegetative"
    assert outcome.session.latest_health_score == 78
    # Weather snapshot captured (farm has GPS; weather service absent → None ok).
    assert outcome.image.week_number == 1
    usage_rows = (await db_session.execute(select(TokenUsage))).scalars().all()
    assert len(usage_rows) == 1
    assert usage_rows[0].module == "growth"


async def test_poor_quality_rejected_before_ai(db_session):
    provider = FakeProvider(make_analysis())
    service = _service(db_session, provider)
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)

    with pytest.raises(PoorImageQualityError) as info:
        await service.upload(user, _req(farm.id, image_base64=_b64(12)))
    assert "too_small" in info.value.issues
    assert provider.calls == 0  # AI never called on a poor image


async def test_no_plant_rejected_and_not_saved(db_session, monkeypatch):
    _accept_quality(monkeypatch)
    provider = FakeProvider(make_analysis(plant=False, reject="building"))
    service = _service(db_session, provider)
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)

    with pytest.raises(NoPlantDetectedError) as info:
        await service.upload(user, _req(farm.id))
    assert info.value.reason == "building"
    rows, total = await service.history(user, page=1, page_size=20)
    assert total == 0


async def test_second_upload_reuses_session_and_computes_delta(db_session, monkeypatch):
    _accept_quality(monkeypatch)
    provider = FakeProvider(make_analysis(health=60))
    service = _service(db_session, provider)
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)

    first = await service.upload(user, _req(farm.id))
    provider.analysis = make_analysis(health=75)  # improved next week
    second = await service.upload(user, _req(farm.id))

    assert second.session.id == first.session.id  # same active session reused
    assert second.session.image_count == 2
    assert second.timeline_entry.health_delta == 15
    # Previous context was passed to the analyzer for comparison.
    assert provider.last_request.previous_context is not None


async def test_history_timeline_latest_and_session_detail(db_session, monkeypatch):
    _accept_quality(monkeypatch)
    service = _service(db_session, FakeProvider(make_analysis()))
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    await service.upload(user, _req(farm.id))
    await service.upload(user, _req(farm.id))

    rows, total = await service.history(user, page=1, page_size=20)
    assert total == 2
    assert all(analysis is not None for _, analysis in rows)

    session, entries = await service.timeline(user, None)
    assert len(entries) == 2
    assert [e.week_number for e, _ in entries] == [1, 1]

    latest = await service.latest(user)
    assert latest is not None and latest[1] is not None

    detail_session, images, timeline = await service.session_detail(user, session.id)
    assert detail_session.id == session.id
    assert len(images) == 2 and len(timeline) == 2


async def test_delete_image_updates_count(db_session, monkeypatch):
    _accept_quality(monkeypatch)
    service = _service(db_session, FakeProvider(make_analysis()))
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    first = await service.upload(user, _req(farm.id))
    await service.upload(user, _req(farm.id))

    await service.delete_image(user, first.image.id)
    rows, total = await service.history(user, page=1, page_size=20)
    assert total == 1
    with pytest.raises(GrowthImageNotFoundError):
        await service.delete_image(user, first.image.id)


async def test_unknown_farm_and_session_raise(db_session, monkeypatch):
    _accept_quality(monkeypatch)
    service = _service(db_session, FakeProvider(make_analysis()))
    user = await _make_user(db_session)
    await _make_farm(db_session, user)

    with pytest.raises(FarmNotFoundError):
        await service.upload(user, _req(uuid.uuid4()))

    farm2 = await _make_farm(db_session, user)
    with pytest.raises(GrowthSessionNotFoundError):
        await service.upload(user, _req(farm2.id, session_id=uuid.uuid4()))


async def test_ownership_isolation(db_session, monkeypatch):
    _accept_quality(monkeypatch)
    service = _service(db_session, FakeProvider(make_analysis()))
    owner = await _make_user(db_session, uid="fb-owner-g")
    other = await _make_user(db_session, uid="fb-other-g")
    farm = await _make_farm(db_session, owner)
    outcome = await service.upload(owner, _req(farm.id))

    with pytest.raises(GrowthImageNotFoundError):
        await service.delete_image(other, outcome.image.id)
    with pytest.raises(GrowthSessionNotFoundError):
        await service.session_detail(other, outcome.session.id)
