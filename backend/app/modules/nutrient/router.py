"""Nutrient Deficiency API routes (docs: brief endpoints; reuse response envelope).

    POST /nutrient/analyze          (analyse a crop photo → corroborated verdict)
    GET  /nutrient/history          (past analyses for a farm, paginated)
    GET  /nutrient/latest           (latest analysis for a farm)
    GET  /nutrient/recommendations  (generic advice from the latest analysis)
    GET  /nutrient/report/{id}      (a full analysis report)

Thin routes — the pipeline, engine and validation live in ``NutrientService``.
Static routes precede any dynamic segment. All endpoints are authenticated.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.modules.nutrient.dependencies import CurrentUser, NutrientServiceDep
from app.modules.nutrient.schemas import (
    AnalyzeNutrientRequest,
    NutrientHistoryOut,
    NutrientRecommendationOut,
    NutrientReportOut,
)
from app.schemas.response import PaginatedData, SuccessResponse, success

router = APIRouter(prefix="/nutrient", tags=["nutrient"])


@router.post(
    "/analyze",
    response_model=SuccessResponse[NutrientReportOut],
    status_code=status.HTTP_201_CREATED,
)
async def analyze(
    payload: AnalyzeNutrientRequest,
    current_user: CurrentUser,
    service: NutrientServiceDep,
):
    """Analyse a crop photo for visible nutrient deficiencies, corroborate with
    Soil / Satellite / Weather, store and return the report."""
    report = await service.analyze(current_user, payload)
    return success(NutrientReportOut.from_report(report), message="Analysis complete")


@router.get("/history", response_model=SuccessResponse[PaginatedData[NutrientHistoryOut]])
async def get_history(
    current_user: CurrentUser,
    service: NutrientServiceDep,
    farm_id: uuid.UUID = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """The farm's nutrient-analysis history (most recent first)."""
    page_data = await service.list_reports(current_user, farm_id, page=page, page_size=page_size)
    return success(
        PaginatedData(
            items=[NutrientReportOut.from_report(r) for r in page_data.items],
            page=page_data.page,
            page_size=page_data.page_size,
            total=page_data.total,
            total_pages=page_data.total_pages,
        )
    )


@router.get("/latest", response_model=SuccessResponse[NutrientReportOut])
async def get_latest(
    current_user: CurrentUser,
    service: NutrientServiceDep,
    farm_id: uuid.UUID = Query(...),
):
    """The most recent nutrient analysis for a farm."""
    report = await service.latest(current_user, farm_id)
    return success(NutrientReportOut.from_report(report))


@router.get(
    "/recommendations",
    response_model=SuccessResponse[list[NutrientRecommendationOut]],
)
async def get_recommendations(
    current_user: CurrentUser,
    service: NutrientServiceDep,
    farm_id: uuid.UUID = Query(...),
):
    """Generic agronomic recommendations from the farm's latest analysis (no brands)."""
    recs = await service.recommendations(current_user, farm_id)
    return success([NutrientRecommendationOut.from_model(r) for r in recs])


@router.get("/report/{report_id}", response_model=SuccessResponse[NutrientReportOut])
async def get_report(
    report_id: uuid.UUID,
    current_user: CurrentUser,
    service: NutrientServiceDep,
):
    """Fetch a full nutrient analysis report."""
    report = await service.get_report(current_user, report_id)
    return success(NutrientReportOut.from_report(report))
