"""Integration tests for the Nutrient service (fake provider + mock storage).

Covers the quality gate, no-plant rejection, corroboration with Soil (confirm) and
Disease (conflict → not confirmed + expert), honest "not confirmed", persistence of
analysis/symptoms/recommendations/history, reads and ownership.
"""
from __future__ import annotations

import base64

import pytest
from app.modules.auth.models import User
from app.modules.disease.models import DiseaseReport
from app.modules.disease.quality import QualityResult
from app.modules.disease.storage import MockStorage
from app.modules.farms.models import Farm, FarmLocation
from app.modules.nutrient import service as service_module
from app.modules.nutrient.exceptions import (
    FarmNotOwnedError,
    NoPlantDetectedError,
    NutrientDataUnavailableError,
    NutrientReportNotFoundError,
    PoorImageQualityError,
)
from app.modules.nutrient.parser import NutrientObservation
from app.modules.nutrient.schemas import AnalyzeNutrientRequest
from app.modules.nutrient.service import NutrientService
from app.modules.soil.models import SoilProfile


def make_observation(
    *, primary: str | None = "nitrogen", plant: bool = True, reject: str | None = None
) -> NutrientObservation:
    return NutrientObservation(
        plant_present=plant,
        reject_reason=reject,
        crop="paddy",
        visible_symptoms=["yellowing", "older_leaf_first"],
        primary=primary,
        secondary=None,
        visual_confidence=68,
        severity="moderate",
        affected_area="widespread",
        explanation_tamil="தமிழ் விளக்கம்",
        explanation_english="english explanation",
        model_used="fake-nutrient",
        raw={"source": "fake"},
    )


class FakeProvider:
    name = "gemini"
    model = "fake-nutrient"

    def __init__(self, observation: NutrientObservation) -> None:
        self.observation = observation
        self.calls = 0

    async def analyze(self, request) -> NutrientObservation:
        self.calls += 1
        return self.observation


def _b64(nbytes: int) -> str:
    return base64.b64encode(b"\x00" * nbytes).decode()


def _accept_quality(monkeypatch) -> None:
    monkeypatch.setattr(
        service_module, "assess_quality", lambda _m: QualityResult(True, [])
    )


def _service(db_session, provider: FakeProvider) -> NutrientService:
    return NutrientService(db_session, provider=provider, storage=MockStorage())


async def _make_user(db_session, uid: str = "fb-nutrient-1") -> User:
    user = User(firebase_uid=uid, status="active")
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_farm(db_session, user: User) -> Farm:
    farm = Farm(user_id=user.id, name="Field A")
    db_session.add(farm)
    await db_session.flush()
    farm.location = FarmLocation(farm_id=farm.id, latitude=10.7, longitude=79.1)
    await db_session.flush()
    return farm


def _request(farm_id, size: int = 64) -> AnalyzeNutrientRequest:
    return AnalyzeNutrientRequest(
        image_base64=_b64(size), mime_type="image/jpeg", farm_id=farm_id
    )


# --------------------------------------------------------------------------- #
# Analyze
# --------------------------------------------------------------------------- #
async def test_analyze_saves_report_with_analysis(db_session, monkeypatch) -> None:
    _accept_quality(monkeypatch)
    provider = FakeProvider(make_observation())
    service = _service(db_session, provider)
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)

    report = await service.analyze(user, _request(farm.id))
    assert provider.calls == 1
    assert report.image_url.startswith("https://r2.mock.local/nutrient/")
    assert report.analysis is not None
    assert report.analysis.primary_deficiency == "nitrogen"
    # No corroboration yet → an honest "possible", not a confirmed claim.
    assert report.analysis.status == "possible"
    assert "yellowing" in [s.code for s in report.symptoms]
    assert any(r.code == "nutrient.rec.nitrogen.deficiency" for r in report.recommendations)


async def test_soil_low_nitrogen_confirms(db_session, monkeypatch) -> None:
    _accept_quality(monkeypatch)
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    # Seed a soil profile that measures nitrogen as low (< 280 kg/ha).
    db_session.add(SoilProfile(user_id=user.id, farm_id=farm.id, nitrogen=200.0))
    await db_session.flush()

    service = _service(db_session, FakeProvider(make_observation(primary="nitrogen")))
    report = await service.analyze(user, _request(farm.id))
    assert report.analysis.status == "confirmed"
    assert report.analysis.soil_reference is not None
    assert report.analysis.needs_test is False


async def test_disease_conflict_downgrades_and_asks_expert(db_session, monkeypatch) -> None:
    _accept_quality(monkeypatch)
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    # A recent high-confidence disease on the same farm → evidence-based conflict.
    db_session.add(
        DiseaseReport(
            user_id=user.id, farm_id=farm.id, image_url="https://r2/x.jpg",
            disease="Leaf blast", confidence=92, language="ta",
        )
    )
    await db_session.flush()

    service = _service(db_session, FakeProvider(make_observation(primary="nitrogen")))
    report = await service.analyze(user, _request(farm.id))
    assert report.analysis.disease_conflict is True
    assert report.analysis.needs_expert is True
    assert report.analysis.status == "not_confirmed"  # never a silent override


async def test_not_confirmed_when_no_visual_finding(db_session, monkeypatch) -> None:
    _accept_quality(monkeypatch)
    service = _service(db_session, FakeProvider(make_observation(primary=None)))
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)

    report = await service.analyze(user, _request(farm.id))
    assert report.analysis.status == "not_confirmed"
    assert report.analysis.primary_deficiency is None  # never fabricated
    assert report.analysis.needs_test is True
    codes = [r.code for r in report.recommendations]
    assert "nutrient.rec.general.not_confirmed" in codes
    assert "nutrient.rec.test.soil_test" in codes


async def test_poor_quality_is_rejected_before_provider(db_session) -> None:
    provider = FakeProvider(make_observation())
    service = _service(db_session, provider)
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)

    with pytest.raises(PoorImageQualityError) as info:
        await service.analyze(user, _request(farm.id, size=12))
    assert "too_small" in info.value.issues
    assert provider.calls == 0  # the model is never called on a poor image


async def test_no_plant_is_rejected_and_not_saved(db_session, monkeypatch) -> None:
    _accept_quality(monkeypatch)
    provider = FakeProvider(make_observation(plant=False, reject="building"))
    service = _service(db_session, provider)
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)

    with pytest.raises(NoPlantDetectedError):
        await service.analyze(user, _request(farm.id))
    page = await service.list_reports(user, farm.id, page=1, page_size=20)
    assert page.total == 0


async def test_recommendations_are_generic_localization_codes(db_session, monkeypatch) -> None:
    _accept_quality(monkeypatch)
    service = _service(db_session, FakeProvider(make_observation()))
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    report = await service.analyze(user, _request(farm.id))
    # No brands — every code is a generic localization key.
    assert all(r.code.startswith("nutrient.rec.") for r in report.recommendations)


# --------------------------------------------------------------------------- #
# Reads + ownership
# --------------------------------------------------------------------------- #
async def test_history_latest_and_get_report(db_session, monkeypatch) -> None:
    _accept_quality(monkeypatch)
    service = _service(db_session, FakeProvider(make_observation()))
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)

    r1 = await service.analyze(user, _request(farm.id))
    await service.analyze(user, _request(farm.id))

    page = await service.list_reports(user, farm.id, page=1, page_size=20)
    assert page.total == 2
    latest = await service.latest(user, farm.id)
    assert latest.analysis is not None
    fetched = await service.get_report(user, r1.id)
    assert fetched.id == r1.id
    recs = await service.recommendations(user, farm.id)
    assert recs  # the latest report's recommendations


async def test_latest_unavailable_before_any_analysis(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(db_session, user)
    service = _service(db_session, FakeProvider(make_observation()))
    with pytest.raises(NutrientDataUnavailableError):
        await service.latest(user, farm.id)


async def test_ownership_isolation(db_session, monkeypatch) -> None:
    _accept_quality(monkeypatch)
    service = _service(db_session, FakeProvider(make_observation()))
    owner = await _make_user(db_session, uid="fb-owner")
    other = await _make_user(db_session, uid="fb-other")
    farm = await _make_farm(db_session, owner)

    with pytest.raises(FarmNotOwnedError):
        await service.analyze(other, _request(farm.id))
    with pytest.raises(NutrientReportNotFoundError):
        import uuid

        await service.get_report(other, uuid.uuid4())
