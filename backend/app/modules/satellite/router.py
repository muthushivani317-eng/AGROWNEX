"""Satellite Intelligence API routes (docs: brief endpoints; reuse envelope).

    GET  /satellite             (dashboard for a farm; honest 'Not Available')
    GET  /satellite/latest      (latest available session)
    GET  /satellite/history     (trend snapshots, paginated)
    GET  /satellite/timeline    (weekly/monthly aggregated indices)
    GET  /satellite/indices     (latest per-index detail)
    GET  /satellite/alerts      (latest session alerts)
    POST /satellite/refresh     (request a new acquisition pass)

Thin routes — the engine, alerts and provider live in ``SatelliteService``.
Static routes precede any dynamic segment. All endpoints are authenticated.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.modules.satellite.constants import TIMELINE_MONTHLY, TIMELINE_WEEKLY
from app.modules.satellite.dependencies import CurrentUser, SatelliteServiceDep
from app.modules.satellite.schemas import (
    SatelliteAlertOut,
    SatelliteDashboardOut,
    SatelliteHistoryOut,
    SatelliteIndexOut,
    SatelliteSessionOut,
    SatelliteTimelineOut,
    TimelinePointOut,
)
from app.schemas.response import PaginatedData, SuccessResponse, success

router = APIRouter(prefix="/satellite", tags=["satellite"])


def _dashboard_out(data: dict) -> SatelliteDashboardOut:
    return SatelliteDashboardOut(
        farm_id=data["farm_id"],
        has_polygon=data["has_polygon"],
        has_data=data["has_data"],
        status=data["status"],
        unavailable_reason=data["unavailable_reason"],
        message_code=data["message_code"],
        session=SatelliteSessionOut.from_session(data["session"]) if data["session"] else None,
        alerts=[SatelliteAlertOut.from_model(a) for a in data["alerts"]],
    )


@router.get("", response_model=SuccessResponse[SatelliteDashboardOut])
async def get_satellite(
    current_user: CurrentUser,
    service: SatelliteServiceDep,
    farm_id: uuid.UUID = Query(...),
):
    """Satellite dashboard — the latest session, health and alerts, or an honest
    'Not Available' / 'add a farm polygon' state."""
    data = await service.get_dashboard(current_user, farm_id)
    return success(_dashboard_out(data))


@router.get("/latest", response_model=SuccessResponse[SatelliteSessionOut])
async def get_latest(
    current_user: CurrentUser,
    service: SatelliteServiceDep,
    farm_id: uuid.UUID = Query(...),
):
    """The most recent *available* satellite session for a farm."""
    session = await service.latest(current_user, farm_id)
    return success(SatelliteSessionOut.from_session(session))


@router.get(
    "/history", response_model=SuccessResponse[PaginatedData[SatelliteHistoryOut]]
)
async def get_history(
    current_user: CurrentUser,
    service: SatelliteServiceDep,
    farm_id: uuid.UUID = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """The farm's vegetation-index trend over time."""
    page_data = await service.history(
        current_user, farm_id, page=page, page_size=page_size
    )
    return success(
        PaginatedData(
            items=[SatelliteHistoryOut.model_validate(h) for h in page_data.items],
            page=page_data.page,
            page_size=page_data.page_size,
            total=page_data.total,
            total_pages=page_data.total_pages,
        )
    )


@router.get("/timeline", response_model=SuccessResponse[SatelliteTimelineOut])
async def get_timeline(
    current_user: CurrentUser,
    service: SatelliteServiceDep,
    farm_id: uuid.UUID = Query(...),
    range: str = Query(TIMELINE_WEEKLY),
):
    """Weekly or monthly aggregated index timeline."""
    range_ = TIMELINE_MONTHLY if range == TIMELINE_MONTHLY else TIMELINE_WEEKLY
    points = await service.timeline(current_user, farm_id, range_=range_)
    return success(
        SatelliteTimelineOut(
            farm_id=farm_id,
            range=range_,
            points=[TimelinePointOut(**p) for p in points],
        )
    )


@router.get("/indices", response_model=SuccessResponse[list[SatelliteIndexOut]])
async def get_indices(
    current_user: CurrentUser,
    service: SatelliteServiceDep,
    farm_id: uuid.UUID = Query(...),
):
    """The latest available session's per-index detail (mean/min/max/std)."""
    rows = await service.indices(current_user, farm_id)
    return success([SatelliteIndexOut.from_model(i) for i in rows])


@router.get("/alerts", response_model=SuccessResponse[list[SatelliteAlertOut]])
async def get_alerts(
    current_user: CurrentUser,
    service: SatelliteServiceDep,
    farm_id: uuid.UUID = Query(...),
):
    """The latest session's satellite alerts."""
    rows = await service.alerts(current_user, farm_id)
    return success([SatelliteAlertOut.from_model(a) for a in rows])


@router.post(
    "/refresh",
    response_model=SuccessResponse[SatelliteSessionOut],
    status_code=status.HTTP_201_CREATED,
)
async def refresh(
    current_user: CurrentUser,
    service: SatelliteServiceDep,
    farm_id: uuid.UUID = Query(...),
):
    """Request a new acquisition pass (honest 'Not Available' if none / no polygon)."""
    session = await service.refresh(current_user, farm_id)
    return success(
        SatelliteSessionOut.from_session(session), message="Satellite refresh complete"
    )
