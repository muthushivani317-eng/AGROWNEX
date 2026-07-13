"""Unit tests for deterministic calendar generation (no DB, no AI)."""
from __future__ import annotations

from datetime import date

from app.modules.calendar.constants import (
    ActivityType,
    Priority,
    Season,
    WeatherDependency,
)
from app.modules.calendar.generator import derive_season, generate_events
from app.modules.calendar.schedules import DEFAULT_SCHEDULE, PADDY_SCHEDULE, get_schedule


def test_generation_is_deterministic_and_dated_from_sowing():
    sowing = date(2026, 6, 15)
    a = generate_events("wheat", sowing)
    b = generate_events("wheat", sowing)
    assert [e.code for e in a] == [e.code for e in b]

    sowing_event = next(e for e in a if e.code == "sowing")
    assert sowing_event.scheduled_date == sowing
    assert sowing_event.day_offset == 0

    land_prep = next(e for e in a if e.code == "land_prep")
    assert land_prep.scheduled_date == date(2026, 6, 3)  # sowing - 12 days


def test_all_twelve_activity_types_are_covered():
    types = {e.activity_type for e in generate_events(None, date(2026, 6, 15))}
    assert types == set(ActivityType)


def test_events_are_sorted_by_date():
    events = generate_events("paddy", date(2026, 6, 15))
    dates = [e.scheduled_date for e in events]
    assert dates == sorted(dates)


def test_crop_specific_schedule_is_used_for_paddy():
    assert get_schedule("paddy") is PADDY_SCHEDULE
    assert get_schedule("unknown-crop") is DEFAULT_SCHEDULE
    assert get_schedule(None) is DEFAULT_SCHEDULE


def test_rainfed_downgrades_irrigation_tasks():
    rainfed = generate_events("wheat", date(2026, 6, 15), irrigation_type="rainfed")
    for event in rainfed:
        if event.weather_dependency == WeatherDependency.IRRIGATION:
            assert event.priority == Priority.LOW
            assert event.reminder_enabled is False


def test_irrigated_farm_keeps_irrigation_priority():
    drip = generate_events("wheat", date(2026, 6, 15), irrigation_type="drip")
    irrigation = [
        e for e in drip if e.weather_dependency == WeatherDependency.IRRIGATION
    ]
    assert irrigation
    assert any(e.priority == Priority.HIGH for e in irrigation)


def test_reminders_can_be_disabled_globally():
    events = generate_events("wheat", date(2026, 6, 15), reminders_enabled=False)
    assert all(e.reminder_enabled is False for e in events)


def test_season_derivation():
    assert derive_season(date(2026, 7, 1)) == Season.KHARIF
    assert derive_season(date(2026, 11, 1)) == Season.RABI
    assert derive_season(date(2026, 1, 15)) == Season.RABI
    assert derive_season(date(2026, 3, 1)) == Season.SUMMER
