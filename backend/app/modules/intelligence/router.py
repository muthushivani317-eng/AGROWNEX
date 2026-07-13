"""Crop Intelligence API routes (docs: brief endpoints; reuse response envelope).

    GET  /intelligence            (farm-health dashboard — latest report or 'refresh')
    GET  /intelligence/latest     (latest report)
    GET  /intelligence/history    (decision trend, paginated)
    GET  /intelligence/report/{id}(a full report)
    POST /intelligence/refresh    (aggregate every module → one new report)

Thin routes — the engine, decision and recommendation logic live in
``IntelligenceService``. Static routes precede any dynamic segment. All endpoints are
authenticated.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.modules.intelligence.dependencies import (
    CurrentUser,
    IntelligenceServiceDep,
)
from app.modules.intelligence.schemas import (
    IntelligenceDashboardOut,
    IntelligenceHistoryOut,
    IntelligenceReportOut,
)
from app.schemas.response import PaginatedData, SuccessResponse, success

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


@router.get("", response_model=SuccessResponse[IntelligenceDashboardOut])
async def get_intelligence(
    current_user: CurrentUser,
    service: IntelligenceServiceDep,
    farm_id: uuid.UUID = Query(...),
):
    """Farm-health dashboard — the latest aggregated report, or a clear 'refresh to
    generate' state."""
    data = await service.get_dashboard(current_user, farm_id)
    return success(
        IntelligenceDashboardOut(
            farm_id=data["farm_id"],
            has_data=data["has_data"],
            message_code=data["message_code"],
            report=IntelligenceReportOut.from_report(data["report"])
            if data["report"]
            else None,
        )
    )


@router.get("/latest", response_model=SuccessResponse[IntelligenceReportOut])
async def get_latest(
    current_user: CurrentUser,
    service: IntelligenceServiceDep,
    farm_id: uuid.UUID = Query(...),
):
    """The most recent intelligence report for a farm."""
    report = await service.latest(current_user, farm_id)
    return success(IntelligenceReportOut.from_report(report))


@router.get(
    "/history",
    response_model=SuccessResponse[PaginatedData[IntelligenceHistoryOut]],
)
async def get_history(
    current_user: CurrentUser,
    service: IntelligenceServiceDep,
    farm_id: uuid.UUID = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """The farm's health/risk trend over time."""
    page_data = await service.history(
        current_user, farm_id, page=page, page_size=page_size
    )
    return success(
        PaginatedData(
            items=[IntelligenceHistoryOut.from_history(h) for h in page_data.items],
            page=page_data.page,
            page_size=page_data.page_size,
            total=page_data.total,
            total_pages=page_data.total_pages,
        )
    )


@router.get("/report/{report_id}", response_model=SuccessResponse[IntelligenceReportOut])
async def get_report(
    report_id: uuid.UUID,
    current_user: CurrentUser,
    service: IntelligenceServiceDep,
):
    """Fetch a full intelligence report."""
    report = await service.get_report(current_user, report_id)
    return success(IntelligenceReportOut.from_report(report))


@router.post(
    "/refresh",
    response_model=SuccessResponse[IntelligenceReportOut],
    status_code=status.HTTP_201_CREATED,
)
async def refresh(
    current_user: CurrentUser,
    service: IntelligenceServiceDep,
    farm_id: uuid.UUID = Query(...),
):
    """Aggregate every module into one new farm-health report."""
    report = await service.refresh(current_user, farm_id)
    return success(
        IntelligenceReportOut.from_report(report), message="Intelligence refreshed"
    )
