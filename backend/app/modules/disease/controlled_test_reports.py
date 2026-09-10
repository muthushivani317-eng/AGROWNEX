"""Persist controlled-test disease-model outcomes in the shared history."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.disease.constants import DISEASE_IMAGE_PREFIX
from app.modules.disease.models import DiseaseReport
from app.modules.disease.repositories import DiseaseReportRepository
from app.modules.disease.storage import get_default_storage, get_private_storage
from app.modules.farms.repositories import FarmRepository


async def persist_controlled_test_report(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    farm_id: uuid.UUID | None,
    image: bytes,
    content_type: str,
    capture_method: str,
    crop: str,
    disease: str | None,
    confidence: float | None,
    model_used: str,
    test_mode: dict,
    outcome: str,
    retain_for_review: bool = True,
    kvk_session: bool = False,
) -> DiseaseReport:
    """Store a model result, including an explicit non-general-release marker."""
    if farm_id is not None:
        farm = await FarmRepository(session).get_for_user(farm_id, user_id)
        if farm is None:
            farm_id = None

    extension = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}.get(
        content_type, "jpg"
    )
    image_url = None
    image_key = None
    if retain_for_review:
        if not settings.private_disease_images_enabled:
            image_url = await get_default_storage().put(
                key=f"{DISEASE_IMAGE_PREFIX}/controlled-test/{user_id}/{uuid.uuid4().hex}.{extension}",
                data=image,
                content_type=content_type,
            )
        try:
            image_key = (
                f"{DISEASE_IMAGE_PREFIX}/controlled-test/{user_id}/"
                f"{uuid.uuid4().hex}.{extension}"
            )
            await get_private_storage().put(key=image_key, data=image, content_type=content_type)
        except Exception:
            image_key = None
    report = DiseaseReport(
        user_id=user_id,
        farm_id=farm_id,
        image_url=image_url,
        image_key=image_key,
        capture_method=capture_method,
        crop=crop,
        disease=disease,
        confidence=round(confidence * 100) if confidence is not None else None,
        needs_expert_review=True,
        review_status=("pending" if retain_for_review else "declined") if kvk_session else None,
        reviewer_role="farmer" if kvk_session else None,
        review_consent=retain_for_review if kvk_session else None,
        kvk_session=kvk_session,
        model_used=model_used,
        # History consumers must retain this marker: these are controlled-test
        # results and are not authorized for general release.
        raw_response={"outcome": outcome, "test_mode": test_mode},
        language="en",
    )
    return await DiseaseReportRepository(session).add(report)
