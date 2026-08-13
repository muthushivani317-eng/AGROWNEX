from __future__ import annotations

import hashlib
import io
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.image_safety import UnsafeImageError, require_safe_image
from app.modules.auth.constants import RoleName
from app.modules.auth.dependencies import ControlledTester, TesterContext, require_any_role
from app.schemas.response import SuccessResponse, success

from .models import DiseaseModelComparison
from .provider import ImageEvidence, OpenAIComparisonError, OpenAIDiseaseComparisonProvider
from .schemas import ComparisonOut, DiagnosticDecision
from .service import decide_comparison, list_comparisons

router = APIRouter(prefix="/disease-comparisons-controlled", tags=["disease-comparisons"])
Reviewer = Annotated[TesterContext, Depends(require_any_role(RoleName.KVK_REVIEWER.value))]
ALLOWED_VIEWS = {"whole_plant", "affected_leaf", "lesion_closeup", "leaf_underside"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 6 * 1024 * 1024
MAX_TOTAL_BYTES = 20 * 1024 * 1024


async def _validated_evidence(upload: UploadFile, view: str) -> ImageEvidence:
    if view not in ALLOWED_VIEWS:
        raise HTTPException(422, detail={"code": "DIAGNOSIS_PHOTO_VIEW_INVALID"})
    content_type = upload.content_type or ""
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(415, detail={"code": "DIAGNOSIS_IMAGE_FORMAT_UNSUPPORTED"})
    payload = await upload.read(MAX_IMAGE_BYTES + 1)
    await upload.close()
    if not payload or len(payload) > MAX_IMAGE_BYTES:
        raise HTTPException(413, detail={"code": "DIAGNOSIS_IMAGE_SIZE_INVALID"})
    try:
        with Image.open(io.BytesIO(payload)) as decoded:
            decoded.load()
            require_safe_image(decoded)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(422, detail={"code": "DIAGNOSIS_IMAGE_UNUSABLE"}) from exc
    except UnsafeImageError as exc:
        raise HTTPException(
            422, detail={"code": "DIAGNOSIS_IMAGE_UNUSABLE", "reason": exc.reason_code}
        ) from exc
    return ImageEvidence(view=view, image=payload, content_type=content_type)


@router.get("", response_model=list[ComparisonOut])
async def comparisons(
    reviewer: Reviewer,
    session: AsyncSession = Depends(get_session),
    limit: int = Query(100, ge=1, le=500),
):
    del reviewer
    rows = await list_comparisons(session, limit=limit)
    return [
        ComparisonOut(
            id=str(row.id),
            subject_hash=hashlib.sha256(str(row.user_id).encode()).hexdigest()[:16],
            crop=row.crop,
            local_model=row.local_model,
            local_status=row.local_status,
            local_label=row.local_label,
            local_confidence=row.local_confidence,
            provider_status=row.provider_status,
            provider_model=row.provider_model,
            provider_label=row.provider_label,
            crop_assessment=row.crop_assessment,
            agrees_with_local=row.agrees_with_local,
            visual_observations=row.visual_observations,
            created_at=row.created_at.isoformat(),
        )
        for row in rows
    ]


@router.post(
    "/guided-evaluation", response_model=SuccessResponse[DiagnosticDecision]
)
async def guided_evaluation(
    tester: ControlledTester,
    images: list[UploadFile] = File(...),
    views: list[str] = Form(...),
    crop: str = Form(..., min_length=1, max_length=40),
    session: AsyncSession = Depends(get_session),
):
    """Controlled, observations-first comparison of an already-classified photo set."""
    if not settings.openai_disease_comparison_enabled:
        raise HTTPException(503, detail={"code": "GUIDED_COMPARISON_DISABLED"})
    if not 1 <= len(images) <= 4 or len(images) != len(views):
        raise HTTPException(422, detail={"code": "DIAGNOSIS_IMAGE_COUNT_INVALID"})
    if len(set(views)) != len(views):
        raise HTTPException(422, detail={"code": "DIAGNOSIS_PHOTO_VIEW_DUPLICATED"})
    evidence = [
        await _validated_evidence(upload, view)
        for upload, view in zip(images, views, strict=True)
    ]
    if sum(len(item.image) for item in evidence) > MAX_TOTAL_BYTES:
        raise HTTPException(413, detail={"code": "DIAGNOSIS_TOTAL_UPLOAD_TOO_LARGE"})

    hashes = [hashlib.sha256(item.image).hexdigest() for item in evidence]
    row = (
        await session.execute(
            select(DiseaseModelComparison)
            .where(
                DiseaseModelComparison.user_id == tester.user.id,
                DiseaseModelComparison.crop == crop,
                DiseaseModelComparison.image_sha256.in_(hashes),
                DiseaseModelComparison.test_mode.is_(True),
            )
            .order_by(DiseaseModelComparison.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(409, detail={"code": "CONFIRMED_CLASSIFIER_RESULT_REQUIRED"})
    try:
        result = await OpenAIDiseaseComparisonProvider().compare_images(
            images=evidence, crop=crop
        )
    except OpenAIComparisonError as exc:
        raise HTTPException(503, detail={"code": str(exc)}) from exc
    return success(
        decide_comparison(
            local_status=row.local_status,
            local_label=row.local_label,
            opinion=result.opinion,
        )
    )
