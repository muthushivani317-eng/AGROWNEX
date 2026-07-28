"""Disease API routes (docs/API_CONTRACT.md → DISEASE DETECTION).

    POST   /disease/analyze
    GET    /disease/history      GET /disease/{id}    DELETE /disease/{id}

Thin routes — the full pipeline lives in ``DiseaseService``.
"""
from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, HTTPException, Query

from app.crop_runtime.registry import load_registry
from app.crop_runtime.schemas import ModelAvailabilityStatus, ModelUnavailableResponse
from app.modules.disease.dependencies import CurrentUser, DiseaseServiceDep
from app.modules.disease.schemas import (
    AnalyzeRequest,
    DiseaseReportOut,
    DiseaseReportSummaryOut,
)
from app.schemas.response import PaginatedData, SuccessResponse, success

router = APIRouter(prefix="/disease", tags=["disease"])


@router.post(
    "/analyze", response_model=SuccessResponse[DiseaseReportOut], status_code=201
)
async def analyze(
    payload: AnalyzeRequest, current_user: CurrentUser, service: DiseaseServiceDep
):
    """Validate a photo, run Gemini vision analysis, store and return the report."""
    if payload.crop:
        try:
            entry = load_registry().get(payload.crop)
        except KeyError:
            entry = None
        if (
            entry is not None
            and entry.model_status == ModelAvailabilityStatus.FROZEN_RUNTIME_READY
            and not entry.disease_detection_enabled
        ):
            unavailable = ModelUnavailableResponse(
                crop_id=entry.crop_id,
                message_en=entry.limitation_message_en,
                message_ta=entry.limitation_message_ta,
                limitation=entry.model_status,
            )
            raise HTTPException(
                status_code=503, detail=unavailable.model_dump(mode="json")
            )
    report = await service.analyze(current_user, payload)
    return success(DiseaseReportOut.from_report(report), message="Analysis complete")


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
    crop: str | None = Query(None),
):
    """List past diagnoses (most recent first; filterable by farm and crop)."""
    items, total = await service.list_reports(
        current_user, page=page, page_size=page_size, farm_id=farm_id, crop=crop
    )
    data = PaginatedData(
        items=[DiseaseReportSummaryOut.model_validate(r) for r in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=math.ceil(total / page_size) if page_size else 0,
    )
    return success(data)


@router.get("/{report_id}", response_model=SuccessResponse[DiseaseReportOut])
async def get_report(
    report_id: uuid.UUID, current_user: CurrentUser, service: DiseaseServiceDep
):
    """Fetch a full disease report."""
    report = await service.get_report(current_user, report_id)
    return success(DiseaseReportOut.from_report(report))


@router.delete("/{report_id}", response_model=SuccessResponse[None])
async def delete_report(
    report_id: uuid.UUID, current_user: CurrentUser, service: DiseaseServiceDep
):
    """Delete a disease report (soft delete)."""
    await service.delete_report(current_user, report_id)
    return success(None, message="Report deleted")
