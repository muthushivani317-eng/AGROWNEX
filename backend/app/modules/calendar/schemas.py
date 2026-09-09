"""Calendar request/response schemas (docs/API_CONTRACT.md → CROP CALENDAR)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.modules.calendar.constants import WeatherAdvisory
from app.modules.calendar.models import CalendarEvent


class GenerateCalendarRequest(BaseModel):
    """Generate (or regenerate) a farm's calendar.

    Inputs default to the farm's own crop / sowing date / irrigation type; the
    optional values are compatibility assertions and must match the owned farm.
    Farmers edit the farm record before generating a different plan, preventing
    one farm's crop or planting date from being applied to another.
    """

    farm_id: uuid.UUID
    crop: str | None = Field(default=None, max_length=80)
    sowing_date: date | None = None
    irrigation_type: str | None = Field(default=None, max_length=40)
    reminders_enabled: bool = True


class UpdateCalendarEventRequest(BaseModel):
    """Update a single activity — used for offline task completion sync."""

    status: str | None = Field(default=None, pattern="^(pending|done|skipped)$")
    reminder_enabled: bool | None = None
    notes: str | None = Field(default=None, max_length=500)


class CalendarEventOut(BaseModel):
    id: uuid.UUID
    farm_id: uuid.UUID
    crop: str | None
    season: str | None
    code: str
    activity_type: str
    title: str
    description: str
    scheduled_date: date
    day_offset: int
    growth_stage: str
    priority: str
    status: str
    weather_dependency: str
    weather_advisory: str = WeatherAdvisory.NONE.value
    reminder_enabled: bool
    reminder_hour: int | None
    completed_at: datetime | None
    notes: str | None
    registry_version: str | None
    registry_verification_status: str | None
    registry_source_reference: str | None
    organic_practice: bool
    created_at: datetime

    @classmethod
    def from_event(
        cls,
        event: CalendarEvent,
        *,
        weather_advisory: str = WeatherAdvisory.NONE.value,
    ) -> CalendarEventOut:
        return cls(
            id=event.id,
            farm_id=event.farm_id,
            crop=event.crop,
            season=event.season,
            code=event.code,
            activity_type=event.activity_type,
            title=event.title,
            description=event.description,
            scheduled_date=event.scheduled_date,
            day_offset=event.day_offset,
            growth_stage=event.growth_stage,
            priority=event.priority,
            status=event.status,
            weather_dependency=event.weather_dependency,
            weather_advisory=weather_advisory,
            reminder_enabled=event.reminder_enabled,
            reminder_hour=event.reminder_hour,
            completed_at=event.completed_at,
            notes=event.notes,
            registry_version=event.registry_version,
            registry_verification_status=event.registry_verification_status,
            registry_source_reference=event.registry_source_reference,
            organic_practice=event.organic_practice,
            created_at=event.created_at,
        )


class CalendarSummaryOut(BaseModel):
    """Progress roll-up for a farm's calendar (drives the progress indicators)."""

    farm_id: uuid.UUID
    crop: str | None
    season: str | None
    total: int
    completed: int
    pending: int
    missed: int
    skipped: int
