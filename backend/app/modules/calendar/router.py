"""Crop Calendar API routes (docs/API_CONTRACT.md → CROP CALENDAR).

    POST /calendar/generate
    GET  /calendar            GET /calendar/today     GET /calendar/upcoming
    GET  /calendar/completed  GET /calendar/missed
    GET  /calendar/summary    GET /calendar/{farm_id}
    PUT  /calendar/events/{event_id}

Thin routes — deterministic generation and weather advisories live in
``CalendarService``.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.modules.action_verification.schemas import ActionOut
from app.modules.calendar.dependencies import CalendarServiceDep, CurrentUser
from app.modules.calendar.schemas import (
    CalendarEventOut,
    CalendarSummaryOut,
    GenerateCalendarRequest,
    UpdateCalendarEventRequest,
)
from app.modules.calendar.service import AnnotatedEvent
from app.schemas.response import SuccessResponse, success

router = APIRouter(prefix="/calendar", tags=["calendar"])


def _out(annotated: list[AnnotatedEvent]) -> list[CalendarEventOut]:
    return [
        CalendarEventOut.from_event(event, weather_advisory=advisory)
        for event, advisory in annotated
    ]


@router.post(
    "/generate",
    response_model=SuccessResponse[list[CalendarEventOut]],
    status_code=201,
)
async def generate_calendar(
    payload: GenerateCalendarRequest,
    current_user: CurrentUser,
    service: CalendarServiceDep,
):
    """Deterministically (re)generate a farm's calendar from its crop schedule."""
    events = await service.generate(current_user, payload)
    return success(_out(events), message="Calendar generated")


@router.get("/today", response_model=SuccessResponse[list[CalendarEventOut]])
async def calendar_today(
    current_user: CurrentUser,
    service: CalendarServiceDep,
    farm_id: uuid.UUID | None = Query(None),
):
    """Activities scheduled for today (optionally filtered by farm)."""
    events = await service.today(current_user, farm_id=farm_id)
    return success(_out(events))


@router.get("/upcoming", response_model=SuccessResponse[list[CalendarEventOut]])
async def calendar_upcoming(
    current_user: CurrentUser,
    service: CalendarServiceDep,
    farm_id: uuid.UUID | None = Query(None),
    days: int = Query(7, ge=1, le=60),
):
    """Pending activities in the next N days."""
    events = await service.upcoming(current_user, farm_id=farm_id, days=days)
    return success(_out(events))


@router.get("/completed", response_model=SuccessResponse[list[CalendarEventOut]])
async def calendar_completed(
    current_user: CurrentUser,
    service: CalendarServiceDep,
    farm_id: uuid.UUID | None = Query(None),
):
    """Completed activities."""
    events = await service.completed(current_user, farm_id=farm_id)
    return success(_out(events))


@router.get("/missed", response_model=SuccessResponse[list[CalendarEventOut]])
async def calendar_missed(
    current_user: CurrentUser,
    service: CalendarServiceDep,
    farm_id: uuid.UUID | None = Query(None),
):
    """Pending activities whose scheduled date has already passed."""
    events = await service.missed(current_user, farm_id=farm_id)
    return success(_out(events))


@router.get("/summary", response_model=SuccessResponse[CalendarSummaryOut])
async def calendar_summary(
    current_user: CurrentUser,
    service: CalendarServiceDep,
    farm_id: uuid.UUID = Query(...),
):
    """Progress roll-up for a farm (drives progress indicators)."""
    data = await service.summary(current_user, farm_id)
    return success(data)


@router.get("", response_model=SuccessResponse[list[CalendarEventOut]])
async def calendar_timeline(
    current_user: CurrentUser,
    service: CalendarServiceDep,
    farm_id: uuid.UUID | None = Query(None),
    crop: str | None = Query(None),
    status: str | None = Query(None, pattern="^(pending|done|skipped)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    organic_only: bool = Query(False),
):
    """Full activity timeline (filterable by farm, crop and status), paginated."""
    events = await service.timeline(
        current_user,
        farm_id=farm_id,
        crop=crop,
        status=status,
        page=page,
        page_size=page_size,
        organic_only=organic_only,
    )
    return success(_out(events))


@router.post("/events/{event_id}/organic-action", response_model=SuccessResponse[ActionOut])
async def register_organic_action(
    event_id: uuid.UUID, current_user: CurrentUser, service: CalendarServiceDep
):
    row = await service.register_organic_action(current_user, event_id)
    return success(ActionOut.from_row(row), message="Organic calendar action registered")


@router.put("/events/{event_id}", response_model=SuccessResponse[CalendarEventOut])
async def update_event(
    event_id: uuid.UUID,
    payload: UpdateCalendarEventRequest,
    current_user: CurrentUser,
    service: CalendarServiceDep,
):
    """Update one activity (status/reminder/notes) — used for offline sync."""
    event, advisory = await service.update_event(current_user, event_id, payload)
    return success(
        CalendarEventOut.from_event(event, weather_advisory=advisory),
        message="Activity updated",
    )


@router.get("/{farm_id}", response_model=SuccessResponse[list[CalendarEventOut]])
async def calendar_for_farm(
    farm_id: uuid.UUID,
    current_user: CurrentUser,
    service: CalendarServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
):
    """Full calendar for a single farm (docs: GET /calendar/{farmId}), paginated."""
    events = await service.for_farm(current_user, farm_id, page=page, page_size=page_size)
    return success(_out(events))
