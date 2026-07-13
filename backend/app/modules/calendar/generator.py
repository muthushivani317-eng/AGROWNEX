"""Deterministic calendar generation (docs: Calendar Generation — no AI in V1).

Pure functions: given a crop, sowing date, season and irrigation type, expand the
predefined schedule templates into concrete dated activities. No database, no
network, no AI — fully reproducible and unit-testable.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from app.modules.calendar.constants import (
    RAINFED_IRRIGATION,
    ActivityType,
    Priority,
    Season,
    WeatherDependency,
)
from app.modules.calendar.schedules import ActivityTemplate, get_schedule


@dataclass(frozen=True)
class GeneratedEvent:
    code: str
    activity_type: ActivityType
    title: str
    description: str
    scheduled_date: date
    priority: Priority
    growth_stage: str
    weather_dependency: WeatherDependency
    reminder_enabled: bool
    day_offset: int


def derive_season(sowing_date: date) -> Season:
    """Map the sowing month to a Tamil Nadu cropping season (deterministic)."""
    month = sowing_date.month
    if 6 <= month <= 9:
        return Season.KHARIF
    if month >= 10 or month == 1:
        return Season.RABI
    return Season.SUMMER


def _is_rainfed(irrigation_type: str | None) -> bool:
    return bool(irrigation_type) and irrigation_type.strip().lower() in RAINFED_IRRIGATION


def _apply_irrigation_policy(
    template: ActivityTemplate, *, rainfed: bool
) -> tuple[Priority, bool]:
    """Rainfed farms rely on rainfall — irrigation tasks are advisory, not urgent."""
    if rainfed and template.weather_dependency == WeatherDependency.IRRIGATION:
        return Priority.LOW, False
    return template.priority, template.reminder_enabled


def generate_events(
    crop: str | None,
    sowing_date: date,
    *,
    irrigation_type: str | None = None,
    reminders_enabled: bool = True,
) -> list[GeneratedEvent]:
    """Expand the crop's schedule into dated events relative to the sowing date."""
    rainfed = _is_rainfed(irrigation_type)
    events: list[GeneratedEvent] = []
    for template in get_schedule(crop):
        priority, reminder = _apply_irrigation_policy(template, rainfed=rainfed)
        events.append(
            GeneratedEvent(
                code=template.code,
                activity_type=template.activity_type,
                title=template.title,
                description=template.description,
                scheduled_date=sowing_date + timedelta(days=template.day_offset),
                priority=priority,
                growth_stage=template.growth_stage.value,
                weather_dependency=template.weather_dependency,
                reminder_enabled=reminder and reminders_enabled,
                day_offset=template.day_offset,
            )
        )
    events.sort(key=lambda e: (e.scheduled_date, e.day_offset))
    return events
