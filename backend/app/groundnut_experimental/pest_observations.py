"""Persistence for farmer-reported Groundnut pest-damage observations.

These records are evidence awaiting human review, never pest identifications.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.disease.constants import DISEASE_IMAGE_PREFIX
from app.modules.disease.models import DiseaseReport
from app.modules.disease.repositories import DiseaseReportRepository
from app.modules.disease.storage import get_private_storage
from app.modules.farms.repositories import FarmRepository


class PestObservationFarmNotFoundError(ValueError):
    pass


async def persist_groundnut_pest_observation(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    farm_id: uuid.UUID | None,
    image: bytes,
    content_type: str,
    capture_method: str,
    damage_extent: str,
    spread_speed: str,
) -> DiseaseReport:
    """Store private farmer evidence without assigning a pest or disease label."""
    if farm_id is not None:
        farm = await FarmRepository(session).get_for_user(farm_id, user_id)
        if farm is None:
            raise PestObservationFarmNotFoundError

    extension = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[
        content_type
    ]
    image_key = (
        f"{DISEASE_IMAGE_PREFIX}/groundnut-pest-observations/{user_id}/"
        f"{uuid.uuid4().hex}.{extension}"
    )
    await get_private_storage().put(
        key=image_key,
        data=image,
        content_type=content_type,
    )

    report = DiseaseReport(
        user_id=user_id,
        farm_id=farm_id,
        image_url=None,
        image_key=image_key,
        capture_method=capture_method,
        crop="groundnut",
        disease=None,
        confidence=None,
        symptoms=None,
        causes=None,
        recommendations=None,
        prevention=None,
        needs_expert_review=True,
        review_status="pending",
        reviewer_role="farmer",
        review_consent=True,
        kvk_session=True,
        model_used=None,
        raw_response={
            "record_type": "farmer_pest_damage_observation",
            "farmer_reported": {
                "damage_extent": damage_extent,
                "spread_speed": spread_speed,
            },
            "diagnosis_assigned": False,
        },
        language="en",
    )
    return await DiseaseReportRepository(session).add(report)
