from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.modules.disease import router as disease_router
from app.modules.disease import schemas as disease_schemas
from app.modules.disease.schemas import DiseaseReportOut, DiseaseReportSummaryOut
from fastapi import HTTPException


def _report(*, image_key: str | None):
    return SimpleNamespace(
        id=uuid4(), farm_id=None, crop="paddy", crop_confidence=90,
        disease="blast", confidence=80, severity="high", symptoms=[], causes=[],
        recommendations=[], prevention=[], conventional_category_english=None,
        conventional_category_tamil=None, visible_parts=[], needs_expert_review=False,
        explanation_tamil=None, explanation_english=None,
        image_url="https://legacy.example/photo.jpg", image_key=image_key,
        thumbnail_url=None, model_used="test", review_status=None, reviewer_role=None,
        corrected_label=None, review_timestamp=None, review_consent=None,
        kvk_session=False, test_mode=None, verification_level=None,
        weather_snapshot=None, latitude=None, longitude=None, language="en",
        created_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
    )


def test_report_contract_announces_private_copy_without_exposing_key():
    report = _report(image_key="disease/farmer/secret-object.jpg")
    full = DiseaseReportOut.from_report(report)
    summary = DiseaseReportSummaryOut.from_report(report)
    assert full.private_image_available is True
    assert summary.private_image_available is True
    assert "image_key" not in full.model_dump()
    assert "image_key" not in summary.model_dump()


def test_cutover_suppresses_public_url_only_when_private_copy_exists(monkeypatch):
    monkeypatch.setattr(disease_schemas.settings, "private_disease_images_enabled", True)
    private = _report(image_key="disease/farmer/private.jpg")
    legacy = _report(image_key=None)
    assert DiseaseReportOut.from_report(private).image_url is None
    assert DiseaseReportSummaryOut.from_report(private).image_url is None
    assert DiseaseReportOut.from_report(legacy).image_url == legacy.image_url


@pytest.mark.asyncio
async def test_private_image_missing_key_returns_safe_404():
    service = SimpleNamespace(get_report=AsyncMock(return_value=_report(image_key=None)))
    with pytest.raises(HTTPException) as raised:
        await disease_router.get_report_image(uuid4(), object(), service)
    assert raised.value.status_code == 404
    assert raised.value.detail == {"code": "IMAGE_NOT_AVAILABLE"}


@pytest.mark.asyncio
async def test_private_image_is_owner_checked_and_never_cached(monkeypatch):
    report = _report(image_key="disease/farmer/private.jpg")
    service = SimpleNamespace(get_report=AsyncMock(return_value=report))
    storage = SimpleNamespace(get=AsyncMock(return_value=b"private-image"))
    monkeypatch.setattr(disease_router, "get_private_storage", lambda: storage)
    user = object()
    response = await disease_router.get_report_image(report.id, user, service)
    service.get_report.assert_awaited_once_with(user, report.id)
    storage.get.assert_awaited_once_with(key=report.image_key)
    assert response.body == b"private-image"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
