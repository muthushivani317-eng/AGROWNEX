"""Integration tests for the disease pipeline (fake vision + mock storage)."""
from __future__ import annotations

import base64
import json

import pytest
from app.modules.auth.models import User
from app.modules.disease import service as service_module
from app.modules.disease.exceptions import (
    DiseaseAnalysisError,
    DiseaseReportNotFoundError,
    NoPlantDetectedError,
    PoorImageQualityError,
)
from app.modules.disease.parser import DiseaseAnalysis
from app.modules.disease.quality import QualityResult
from app.modules.disease.schemas import AnalyzeRequest
from app.modules.disease.service import DiseaseService
from app.modules.disease.storage import MockStorage
from app.modules.disease.vision import AnalysisRequest, GeminiVisionProvider


def make_analysis(*, plant: bool = True, reject: str | None = None) -> DiseaseAnalysis:
    return DiseaseAnalysis(
        plant_present=plant,
        reject_reason=reject,
        visible_parts=["leaf"],
        crop="paddy",
        crop_confidence=80,
        disease="Leaf blast",
        confidence=77,
        severity="moderate",
        symptoms=["grey lesions"],
        causes=["fungus"],
        recommendations=["remove affected leaves"],
        prevention=["treat seeds"],
        needs_expert_review=False,
        explanation_tamil="தமிழ் விளக்கம்",
        explanation_english="english explanation",
        model_used="fake-vision",
        raw={"source": "fake"},
    )


class FakeProvider:
    model = "fake-vision"

    def __init__(self, analysis: DiseaseAnalysis) -> None:
        self.analysis = analysis
        self.calls = 0

    async def analyze(self, request) -> DiseaseAnalysis:
        self.calls += 1
        return self.analysis


def _b64(nbytes: int) -> str:
    return base64.b64encode(b"\x00" * nbytes).decode()


async def _make_user(db_session, uid: str = "fb-disease-1") -> User:
    user = User(
        firebase_uid=uid,
        phone_number="+919876533333",
        email=None,
        is_phone_verified=True,
        is_email_verified=False,
        status="active",
    )
    db_session.add(user)
    await db_session.flush()
    return user


def _accept_quality(monkeypatch) -> None:
    monkeypatch.setattr(
        service_module, "assess_quality", lambda _m: QualityResult(True, [])
    )


def _service(db_session, provider) -> DiseaseService:
    return DiseaseService(db_session, provider=provider, storage=MockStorage())


async def test_analyze_saves_report(db_session, monkeypatch):
    _accept_quality(monkeypatch)
    provider = FakeProvider(make_analysis())
    service = _service(db_session, provider)
    user = await _make_user(db_session)

    report = await service.analyze(
        user, AnalyzeRequest(image_base64=_b64(64), mime_type="image/jpeg")
    )
    assert provider.calls == 1
    assert report.disease == "Leaf blast"
    assert report.confidence == 77
    assert report.model_used == "fake-vision"
    assert report.image_url.startswith("https://r2.mock.local/disease/")
    assert report.explanation_tamil == "தமிழ் விளக்கம்"

    fetched = await service.get_report(user, report.id)
    assert fetched.id == report.id


async def test_poor_quality_is_rejected_before_ai(db_session):
    provider = FakeProvider(make_analysis())
    service = _service(db_session, provider)
    user = await _make_user(db_session)

    with pytest.raises(PoorImageQualityError) as info:
        await service.analyze(
            user, AnalyzeRequest(image_base64=_b64(12), mime_type="image/jpeg")
        )
    assert "too_small" in info.value.issues
    assert provider.calls == 0  # AI never called on a poor image


async def test_no_plant_is_rejected_and_not_saved(db_session, monkeypatch):
    _accept_quality(monkeypatch)
    provider = FakeProvider(make_analysis(plant=False, reject="building"))
    service = _service(db_session, provider)
    user = await _make_user(db_session)

    with pytest.raises(NoPlantDetectedError) as info:
        await service.analyze(
            user, AnalyzeRequest(image_base64=_b64(64), mime_type="image/jpeg")
        )
    assert info.value.reason == "building"
    _, total = await service.list_reports(user, page=1, page_size=20)
    assert total == 0


async def test_history_and_delete(db_session, monkeypatch):
    _accept_quality(monkeypatch)
    service = _service(db_session, FakeProvider(make_analysis()))
    user = await _make_user(db_session)

    r1 = await service.analyze(
        user, AnalyzeRequest(image_base64=_b64(64), mime_type="image/jpeg")
    )
    await service.analyze(
        user, AnalyzeRequest(image_base64=_b64(64), mime_type="image/jpeg")
    )
    _, total = await service.list_reports(user, page=1, page_size=20)
    assert total == 2

    await service.delete_report(user, r1.id)
    _, after = await service.list_reports(user, page=1, page_size=20)
    assert after == 1
    with pytest.raises(DiseaseReportNotFoundError):
        await service.get_report(user, r1.id)


async def test_ownership_isolation(db_session, monkeypatch):
    _accept_quality(monkeypatch)
    service = _service(db_session, FakeProvider(make_analysis()))
    owner = await _make_user(db_session, uid="fb-owner")
    other = await _make_user(db_session, uid="fb-other")

    report = await service.analyze(
        owner, AnalyzeRequest(image_base64=_b64(64), mime_type="image/jpeg")
    )
    with pytest.raises(DiseaseReportNotFoundError):
        await service.get_report(other, report.id)


# --- Vision provider parse-retry (STEP 5), no DB / no network ---
class RetryVision(GeminiVisionProvider):
    def __init__(self, outputs: list[str]) -> None:
        super().__init__(api_key="test-key")
        self._outputs = outputs
        self._index = 0

    async def _generate(self, request) -> str:
        out = self._outputs[self._index]
        self._index += 1
        return out


_GOOD_JSON = json.dumps(
    {
        "plant_present": True,
        "crop": "paddy",
        "crop_confidence": 80,
        "disease": "Leaf blast",
        "confidence": 70,
        "severity": "low",
        "symptoms": ["spots"],
        "causes": ["fungus"],
        "recommendations": ["prune"],
        "prevention": ["rotate"],
        "needs_expert_review": False,
        "explanation_tamil": "ta",
        "explanation_english": "en",
    }
)


async def test_vision_retries_once_on_bad_json():
    provider = RetryVision(["not json at all", _GOOD_JSON])
    result = await provider.analyze(
        AnalysisRequest(
            image_base64="x", mime_type="image/jpeg", crop="paddy",
            language="ta", farm_context="",
        )
    )
    assert result.disease == "Leaf blast"
    assert provider._index == 2  # retried exactly once


async def test_vision_gives_up_after_retry():
    provider = RetryVision(["bad", "still bad"])
    with pytest.raises(DiseaseAnalysisError):
        await provider.analyze(
            AnalysisRequest(
                image_base64="x", mime_type="image/jpeg", crop=None,
                language="en", farm_context="",
            )
        )
