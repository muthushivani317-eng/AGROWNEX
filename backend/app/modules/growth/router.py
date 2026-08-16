"""Growth API routes (docs/API_CONTRACT.md → CROP GROWTH).

    POST   /growth/upload
    GET    /growth/history        GET /growth/timeline    GET /growth/latest
    GET    /growth/session/{id}   DELETE /growth/image/{id}

Thin routes — the upload pipeline lives in ``GrowthService``. Every response uses
the global envelope.
"""

from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, HTTPException, Query

from app.modules.growth.dependencies import CurrentUser, GrowthServiceDep, StageTrackingServiceDep
from app.modules.growth.schemas import (
    GrowthImageOut,
    GrowthSessionDetailOut,
    GrowthSessionOut,
    GrowthTimelineOut,
    StageStateOut,
    StageTransitionOut,
    StageTransitionRequest,
    TimelineEntryOut,
    UploadGrowthRequest,
    UploadResultOut,
)
from app.modules.growth.stage_service import StageConflictError
from app.modules.growth.stage_tracking import StageEvidence, TransitionError
from app.schemas.response import PaginatedData, SuccessResponse, success

router = APIRouter(prefix="/growth", tags=["growth"])


@router.post("/upload", response_model=SuccessResponse[UploadResultOut], status_code=201)
async def upload(
    payload: UploadGrowthRequest,
    current_user: CurrentUser,
    service: GrowthServiceDep,
):
    """Validate a crop photo, run growth analysis, store it and update the timeline."""
    outcome = await service.upload(current_user, payload)
    result = UploadResultOut(
        session=GrowthSessionOut.from_row(outcome.session),
        image=GrowthImageOut.from_row(outcome.image, analysis=outcome.analysis),
        timeline_entry=TimelineEntryOut.from_row(outcome.timeline_entry, image=outcome.image),
    )
    return success(result, message="Photo added to growth history")


@router.get("/history", response_model=SuccessResponse[PaginatedData[GrowthImageOut]])
async def history(
    current_user: CurrentUser,
    service: GrowthServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session_id: uuid.UUID | None = Query(None),
    farm_id: uuid.UUID | None = Query(None),
):
    """All uploaded photos (most recent first), with their analysis."""
    rows, total = await service.history(
        current_user,
        page=page,
        page_size=page_size,
        session_id=session_id,
        farm_id=farm_id,
    )
    data = PaginatedData(
        items=[GrowthImageOut.from_row(image, analysis=analysis) for image, analysis in rows],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=math.ceil(total / page_size) if page_size else 0,
    )
    return success(data)


@router.get("/timeline", response_model=SuccessResponse[GrowthTimelineOut])
async def timeline(
    current_user: CurrentUser,
    service: GrowthServiceDep,
    session_id: uuid.UUID | None = Query(None),
    farm_id: uuid.UUID | None = Query(None),
):
    """Week 1 → Week N growth timeline for a session (defaults to the latest)."""
    session, entries = await service.timeline(current_user, session_id, farm_id=farm_id)
    data = GrowthTimelineOut(
        session=GrowthSessionOut.from_row(session),
        timeline=[TimelineEntryOut.from_row(entry, image=image) for entry, image in entries],
    )
    return success(data)


@router.get("/latest", response_model=SuccessResponse[GrowthImageOut | None])
async def latest(
    current_user: CurrentUser,
    service: GrowthServiceDep,
):
    """The most recent uploaded photo + analysis (null if none yet)."""
    result = await service.latest(current_user)
    if result is None:
        return success(None)
    image, analysis = result
    return success(GrowthImageOut.from_row(image, analysis=analysis))


@router.get(
    "/session/{session_id}",
    response_model=SuccessResponse[GrowthSessionDetailOut],
)
async def session_detail(
    session_id: uuid.UUID,
    current_user: CurrentUser,
    service: GrowthServiceDep,
):
    """Full session: metadata, all photos (with analysis) and the timeline."""
    session, images, timeline_rows = await service.session_detail(current_user, session_id)
    base = GrowthSessionOut.from_row(session)
    data = GrowthSessionDetailOut(
        **base.model_dump(),
        images=[GrowthImageOut.from_row(image, analysis=analysis) for image, analysis in images],
        timeline=[TimelineEntryOut.from_row(entry, image=image) for entry, image in timeline_rows],
    )
    return success(data)


@router.delete("/image/{image_id}", response_model=SuccessResponse[None])
async def delete_image(
    image_id: uuid.UUID,
    current_user: CurrentUser,
    service: GrowthServiceDep,
):
    """Delete an uploaded growth photo (soft delete)."""
    await service.delete_image(current_user, image_id)
    return success(None, message="Photo deleted")


@router.get("/stage", response_model=SuccessResponse[StageStateOut | None])
async def current_stage(
    current_user: CurrentUser,
    service: StageTrackingServiceDep,
    farm_id: uuid.UUID = Query(...),
    crop_cycle_id: str = Query(..., min_length=1, max_length=80),
):
    return success(await service.current(current_user, farm_id, crop_cycle_id))


@router.post("/stage/transition", response_model=SuccessResponse[StageStateOut])
async def transition_stage_state(
    payload: StageTransitionRequest,
    current_user: CurrentUser,
    service: StageTrackingServiceDep,
):
    evidence = StageEvidence(**payload.evidence.model_dump())
    if payload.expert_reviewed:
        raise HTTPException(
            status_code=403,
            detail={"code": "EXPERT_REVIEW_CANNOT_BE_SELF_ASSERTED"},
        )
    try:
        row = await service.apply(
            current_user,
            farm_id=payload.farm_id,
            crop_cycle_id=payload.crop_cycle_id,
            event=payload.event,
            stage=payload.stage,
            expected_version=payload.expected_version,
            idempotency_key=payload.idempotency_key,
            evidence=evidence,
            reason=payload.reason,
            photo_reference=payload.photo_reference,
            expert_reviewed=payload.expert_reviewed,
            allow_large_jump=payload.allow_large_jump,
        )
    except (StageConflictError, TransitionError) as exc:
        raise HTTPException(status_code=409, detail={"code": str(exc)}) from exc
    return success(row)


@router.get(
    "/stage/{state_id}/history",
    response_model=SuccessResponse[list[StageTransitionOut]],
)
async def stage_history(
    state_id: uuid.UUID,
    current_user: CurrentUser,
    service: StageTrackingServiceDep,
):
    return success(await service.history(current_user, state_id))
