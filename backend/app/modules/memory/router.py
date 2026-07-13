"""Farm Memory API routes (docs: brief endpoints; reuse response envelope).

    GET  /memory          (dashboard — recent memories + latest summary)
    GET  /memory/latest   (most recent memory)
    GET  /memory/history  (full timeline, paginated + filterable)
    GET  /memory/summary  (seasonal + yearly summaries)
    GET  /memory/{id}     (one memory + its links)
    POST /memory/rebuild  (deterministically regenerate memory from every module)

Thin routes — the engine, merge, summary and link logic live in ``MemoryService``.
Static routes precede the dynamic ``/{id}`` segment. All endpoints are authenticated
and ownership-scoped.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.modules.memory.constants import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    SummaryPeriod,
)
from app.modules.memory.dependencies import CurrentUser, MemoryServiceDep
from app.modules.memory.schemas import (
    MemoryDashboardOut,
    MemoryOut,
    MemoryRebuildOut,
    MemorySummaryBundleOut,
    MemorySummaryOut,
)
from app.schemas.response import PaginatedData, SuccessResponse, success

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("", response_model=SuccessResponse[MemoryDashboardOut])
async def get_memory(
    current_user: CurrentUser,
    service: MemoryServiceDep,
    farm_id: uuid.UUID = Query(...),
):
    """Farm memory dashboard — the most recent memories and the latest summary."""
    data = await service.get_dashboard(current_user, farm_id)
    return success(
        MemoryDashboardOut(
            farm_id=data["farm_id"],
            has_data=data["has_data"],
            total=data["total"],
            message_code=data["message_code"],
            recent=[MemoryOut.from_memory(m) for m in data["recent"]],
            latest_summary=MemorySummaryOut.from_summary(data["latest_summary"])
            if data["latest_summary"]
            else None,
        )
    )


@router.get("/latest", response_model=SuccessResponse[MemoryOut])
async def get_latest(
    current_user: CurrentUser,
    service: MemoryServiceDep,
    farm_id: uuid.UUID = Query(...),
):
    """The most recent memory for a farm."""
    memory = await service.latest(current_user, farm_id)
    return success(MemoryOut.from_memory(memory))


@router.get("/history", response_model=SuccessResponse[PaginatedData[MemoryOut]])
async def get_history(
    current_user: CurrentUser,
    service: MemoryServiceDep,
    farm_id: uuid.UUID = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    source_module: str | None = Query(None),
    season: str | None = Query(None),
    crop: str | None = Query(None),
    importance: str | None = Query(None),
    q: str | None = Query(None),
):
    """The farm's full memory timeline (newest first), filterable + searchable."""
    page_data = await service.history(
        current_user,
        farm_id,
        page=page,
        page_size=page_size,
        source_module=source_module,
        season=season,
        crop=crop,
        importance=importance,
        search=q,
    )
    return success(
        PaginatedData(
            items=[MemoryOut.from_memory(m) for m in page_data.items],
            page=page_data.page,
            page_size=page_data.page_size,
            total=page_data.total,
            total_pages=page_data.total_pages,
        )
    )


@router.get("/summary", response_model=SuccessResponse[MemorySummaryBundleOut])
async def get_summary(
    current_user: CurrentUser,
    service: MemoryServiceDep,
    farm_id: uuid.UUID = Query(...),
):
    """Generated seasonal and yearly summaries for a farm."""
    rows = await service.summaries(current_user, farm_id)
    seasons = [
        MemorySummaryOut.from_summary(s)
        for s in rows
        if s.period_type == SummaryPeriod.SEASON.value
    ]
    years = [
        MemorySummaryOut.from_summary(s)
        for s in rows
        if s.period_type == SummaryPeriod.YEAR.value
    ]
    return success(
        MemorySummaryBundleOut(farm_id=farm_id, seasons=seasons, years=years)
    )


@router.get("/{memory_id}", response_model=SuccessResponse[MemoryOut])
async def get_one(
    memory_id: uuid.UUID,
    current_user: CurrentUser,
    service: MemoryServiceDep,
):
    """Fetch a single memory and its related-memory links."""
    memory, links = await service.get_memory(current_user, memory_id)
    return success(MemoryOut.from_memory(memory, links=links))


@router.post(
    "/rebuild",
    response_model=SuccessResponse[MemoryRebuildOut],
    status_code=status.HTTP_201_CREATED,
)
async def rebuild(
    current_user: CurrentUser,
    service: MemoryServiceDep,
    farm_id: uuid.UUID = Query(...),
):
    """Deterministically rebuild the farm's memory from every module."""
    result = await service.rebuild(current_user, farm_id)
    return success(
        MemoryRebuildOut(
            farm_id=farm_id,
            created=result.created,
            total=result.total,
            summaries=result.summaries,
            links=result.links,
        ),
        message="Memory rebuilt",
    )
