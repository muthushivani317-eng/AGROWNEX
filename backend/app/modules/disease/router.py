"""Disease API routes (docs/API_CONTRACT.md → DISEASE DETECTION).

    GET    /disease/history      GET /disease/{id}    DELETE /disease/{id}

Thin routes — the full pipeline lives in ``DiseaseService``.
"""

from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.auth.constants import RoleName
from app.modules.auth.dependencies import TesterContext, require_any_role
from app.modules.disease.capability_service import (
    DiseaseCapabilitiesResponse,
    disease_capabilities_for_user,
)
from app.modules.disease.dependencies import CurrentUser, DiseaseServiceDep
from app.modules.disease.farmer_diagnosis_service import (
    DiseaseDiagnosisError,
    diagnose_for_farmer,
)
from app.modules.disease.ml_runtime import get_model_runtime
from app.modules.disease.review import (
    get_pending_groundnut_pest_observation,
    complete_groundnut_pest_observation,
    groundnut_pest_observation_for_review,
    list_pending_groundnut_pest_observations,
    review_redgram_report,
)
from app.modules.disease.schemas import (
    DiseaseReportOut,
    DiseaseReportSummaryOut,
    DiseaseReviewOut,
    DiseaseReviewRequest,
    GroundnutPestObservationReviewOut,
    GroundnutPestObservationCompletionOut,
    GroundnutPestObservationCompletionRequest,
    ModelMetadataOut,
)
from app.modules.disease.storage import get_private_storage
from app.schemas.response import PaginatedData, SuccessResponse, success

router = APIRouter(prefix="/disease", tags=["disease"])


async def require_kvk_reviewer(
    reviewer: TesterContext = Depends(require_any_role(RoleName.KVK_REVIEWER.value)),
) -> TesterContext:
    return reviewer

_DIAGNOSIS_ERROR_STATUS = {
    "IMAGE_FORMAT_UNSUPPORTED": 415,
    "IMAGE_SIZE_INVALID": 413,
    "IMAGE_UNUSABLE": 422,
    "DIAGNOSIS_TEMPORARILY_UNAVAILABLE": 503,
}


@router.post("/predict", response_model=SuccessResponse[DiseaseReportOut])
async def predict_disease(
    current_user: CurrentUser,
    image: UploadFile = File(...),
    crop: str = Form(..., min_length=1, max_length=40),
    farm_id: uuid.UUID | None = Form(None),
    session: AsyncSession = Depends(get_session),
):
    """Farmer-facing diagnosis (general release — any authenticated farmer).

    Primary signal is an OpenAI vision read of the photo; a purpose-trained
    local classifier (banana/chilli/redgram) is consulted as a supporting
    check when available. See ``farmer_diagnosis_service`` for why OpenAI is
    authoritative rather than the local model's own (unvalidated) confidence.
    """
    payload = await image.read()
    await image.close()
    try:
        report = await diagnose_for_farmer(
            session,
            user=current_user,
            crop=crop,
            farm_id=farm_id,
            image_bytes=payload,
            content_type=image.content_type or "image/jpeg",
        )
    except DiseaseDiagnosisError as exc:
        status_code = _DIAGNOSIS_ERROR_STATUS.get(exc.code, 422)
        raise HTTPException(status_code, detail={"code": exc.code}) from exc
    return success(DiseaseReportOut.from_report(report))


@router.post("/{report_id}/kvk-review", response_model=DiseaseReviewOut)
async def save_kvk_review(
    report_id: uuid.UUID,
    payload: DiseaseReviewRequest,
    reviewer: TesterContext = Depends(require_any_role(RoleName.KVK_REVIEWER.value)),
    session: AsyncSession = Depends(get_session),
):
    del reviewer
    try:
        report = await review_redgram_report(
            session,
            report_id=report_id,
            correct=payload.correct,
            corrected_label=payload.corrected_label,
        )
    except LookupError as exc:
        raise HTTPException(404, detail={"code": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(422, detail={"code": str(exc)}) from exc
    return DiseaseReviewOut(
        report_id=report.id,
        review_status=report.review_status,
        corrected_label=report.corrected_label,
        reviewer_role="kvk_officer",
        review_timestamp=report.review_timestamp,
    )


@router.get(
    "/kvk/groundnut-pest-observations",
    response_model=list[GroundnutPestObservationReviewOut],
)
async def list_groundnut_pest_observations_for_review(
    reviewer: TesterContext = Depends(require_kvk_reviewer),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    del reviewer
    return await list_pending_groundnut_pest_observations(
        session, limit=limit, offset=offset
    )


@router.get(
    "/kvk/groundnut-pest-observations/{observation_id}",
    response_model=GroundnutPestObservationReviewOut,
)
async def inspect_groundnut_pest_observation(
    observation_id: uuid.UUID,
    reviewer: TesterContext = Depends(require_kvk_reviewer),
    session: AsyncSession = Depends(get_session),
):
    del reviewer
    try:
        record = await get_pending_groundnut_pest_observation(session, observation_id)
    except LookupError as exc:
        raise HTTPException(404, detail={"code": str(exc)}) from exc
    return groundnut_pest_observation_for_review(record)


@router.get("/kvk/groundnut-pest-observations/{observation_id}/image")
async def get_groundnut_pest_observation_image(
    observation_id: uuid.UUID,
    reviewer: TesterContext = Depends(require_kvk_reviewer),
    session: AsyncSession = Depends(get_session),
):
    del reviewer
    try:
        record = await get_pending_groundnut_pest_observation(session, observation_id)
    except LookupError as exc:
        raise HTTPException(404, detail={"code": str(exc)}) from exc
    if not record.image_key:
        raise HTTPException(404, detail={"code": "IMAGE_NOT_AVAILABLE"})
    ext = record.image_key.rsplit(".", 1)[-1].lower()
    media_type = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }.get(ext, "application/octet-stream")
    data = await get_private_storage().get(key=record.image_key)
    return Response(
        content=data,
        media_type=media_type,
        headers={
            "Cache-Control": "private, no-store",
            "Content-Disposition": "inline",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post(
    "/kvk/groundnut-pest-observations/{observation_id}/complete",
    response_model=GroundnutPestObservationCompletionOut,
)
async def complete_groundnut_pest_observation_review(
    observation_id: uuid.UUID,
    payload: GroundnutPestObservationCompletionRequest,
    reviewer: TesterContext = Depends(require_kvk_reviewer),
    session: AsyncSession = Depends(get_session),
):
    del reviewer
    try:
        record = await complete_groundnut_pest_observation(
            session,
            report_id=observation_id,
            feedback=payload.feedback,
        )
    except LookupError as exc:
        raise HTTPException(404, detail={"code": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(422, detail={"code": str(exc)}) from exc
    except RuntimeError as exc:
        raise HTTPException(409, detail={"code": str(exc)}) from exc
    return GroundnutPestObservationCompletionOut(
        observation_id=record.id,
        feedback=record.raw_response["review"]["feedback"],
        review_timestamp=record.review_timestamp,
    )


@router.get("/model-metadata", response_model=SuccessResponse[ModelMetadataOut])
async def model_metadata(current_user: CurrentUser):
    del current_user
    return success(ModelMetadataOut.model_validate(get_model_runtime().metadata()))


@router.get(
    "/capabilities",
    response_model=SuccessResponse[DiseaseCapabilitiesResponse],
)
async def crop_capabilities(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
):
    return success(await disease_capabilities_for_user(current_user, session))


@router.get(
    "/history",
    response_model=SuccessResponse[PaginatedData[DiseaseReportSummaryOut]],
)
async def list_history(
    current_user: CurrentUser,
    service: DiseaseServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    farm_id: uuid.UUID | None = Query(None),
    unassigned_only: bool = Query(False),
    crop: str | None = Query(None),
):
    """List past diagnoses (most recent first; filterable by farm and crop)."""
    items, total = await service.list_reports(
        current_user,
        page=page,
        page_size=page_size,
        farm_id=farm_id,
        unassigned_only=unassigned_only,
        crop=crop,
    )
    data = PaginatedData(
        items=[DiseaseReportSummaryOut.from_report(r) for r in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=math.ceil(total / page_size) if page_size else 0,
    )
    return success(data)


@router.get("/{report_id}", response_model=SuccessResponse[DiseaseReportOut])
async def get_report(report_id: uuid.UUID, current_user: CurrentUser, service: DiseaseServiceDep):
    """Fetch a full disease report."""
    report = await service.get_report(current_user, report_id)
    return success(DiseaseReportOut.from_report(report))


@router.get("/{report_id}/image")
async def get_report_image(
    report_id: uuid.UUID, current_user: CurrentUser, service: DiseaseServiceDep
):
    """Serve a report photo from private storage after ownership validation."""
    report = await service.get_report(current_user, report_id)
    if not report.image_key:
        raise HTTPException(404, detail={"code": "IMAGE_NOT_AVAILABLE"})
    ext = report.image_key.rsplit(".", 1)[-1].lower()
    media_type = {
        "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp",
    }.get(ext, "application/octet-stream")
    data = await get_private_storage().get(key=report.image_key)
    return Response(
        content=data,
        media_type=media_type,
        headers={
            "Cache-Control": "private, no-store",
            "Content-Disposition": "inline",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/{report_id}", response_model=SuccessResponse[None])
async def delete_report(
    report_id: uuid.UUID, current_user: CurrentUser, service: DiseaseServiceDep
):
    """Delete a disease report (soft delete)."""
    await service.delete_report(current_user, report_id)
    return success(None, message="Report deleted")
