"""Soil Intelligence API routes (docs: brief endpoints; reuse response envelope).

    GET  /soil                 (soil dashboard for a farm; honest 'no data' state)
    GET  /soil/latest          (latest soil report for a farm)
    GET  /soil/history         (soil value trend, paginated)
    GET  /soil/recommendation  (generic agronomic recommendations)
    POST /soil/report          (upload a soil report + values → assess + advise)

Thin routes — assessment, the engine and validation live in ``SoilService``.
Static routes precede any dynamic segment. All endpoints are authenticated.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.modules.soil.dependencies import CurrentUser, SoilServiceDep
from app.modules.soil.schemas import (
    SoilAssessmentOut,
    SoilDashboardOut,
    SoilHistoryOut,
    SoilProfileOut,
    SoilRecommendationOut,
    SoilReportCreate,
    SoilReportOut,
)
from app.schemas.response import PaginatedData, SuccessResponse, success

router = APIRouter(prefix="/soil", tags=["soil"])


def _dashboard_out(data: dict) -> SoilDashboardOut:
    return SoilDashboardOut(
        farm_id=data["farm_id"],
        has_data=data["has_data"],
        message_code=data["message_code"],
        profile=SoilProfileOut.from_profile(data["profile"]) if data["profile"] else None,
        assessment=(
            SoilAssessmentOut.from_assessment(data["assessment"])
            if data["assessment"]
            else None
        ),
        recommendations=[
            SoilRecommendationOut.from_draft(d) for d in data["recommendations"]
        ],
        latest_report=(
            SoilReportOut.from_report(data["latest_report"])
            if data["latest_report"]
            else None
        ),
    )


@router.get("", response_model=SuccessResponse[SoilDashboardOut])
async def get_soil(
    current_user: CurrentUser,
    service: SoilServiceDep,
    farm_id: uuid.UUID = Query(...),
):
    """Soil dashboard for a farm — profile, assessment and generic advice, or a
    clear 'no data available' state (soil values are never fabricated)."""
    data = await service.get_dashboard(current_user, farm_id)
    return success(_dashboard_out(data))


@router.get("/latest", response_model=SuccessResponse[SoilReportOut])
async def get_latest(
    current_user: CurrentUser,
    service: SoilServiceDep,
    farm_id: uuid.UUID = Query(...),
):
    """The most recent soil report for a farm."""
    report = await service.latest(current_user, farm_id)
    return success(SoilReportOut.from_report(report))


@router.get(
    "/history", response_model=SuccessResponse[PaginatedData[SoilHistoryOut]]
)
async def get_history(
    current_user: CurrentUser,
    service: SoilServiceDep,
    farm_id: uuid.UUID = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """The farm's soil value trend over time."""
    page_data = await service.history(
        current_user, farm_id, page=page, page_size=page_size
    )
    return success(
        PaginatedData(
            items=[SoilHistoryOut.model_validate(h) for h in page_data.items],
            page=page_data.page,
            page_size=page_data.page_size,
            total=page_data.total,
            total_pages=page_data.total_pages,
        )
    )


@router.get(
    "/recommendation", response_model=SuccessResponse[list[SoilRecommendationOut]]
)
async def get_recommendations(
    current_user: CurrentUser,
    service: SoilServiceDep,
    farm_id: uuid.UUID = Query(...),
):
    """Generic agronomic recommendations (no commercial brands)."""
    drafts = await service.recommendations(current_user, farm_id)
    return success([SoilRecommendationOut.from_draft(d) for d in drafts])


@router.post(
    "/report",
    response_model=SuccessResponse[SoilReportOut],
    status_code=status.HTTP_201_CREATED,
)
async def submit_report(
    payload: SoilReportCreate,
    current_user: CurrentUser,
    service: SoilServiceDep,
):
    """Upload a soil report (values + optional image) — it is assessed and advised."""
    _profile, report = await service.submit_report(current_user, payload)
    return success(SoilReportOut.from_report(report), message="Soil report saved")
