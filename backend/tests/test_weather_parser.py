"""Unit tests for the Open-Meteo parser (pure, no network)."""
from __future__ import annotations

from app.modules.weather.parser import (
    parse_current,
    parse_daily,
    parse_hourly,
    parse_location,
)

from tests.weather_fixture import build_raw


def test_parse_current():
    current = parse_current(build_raw())
    assert current.temperature_c == 30.0
    assert current.apparent_temperature_c == 32.0
    assert current.humidity_pct == 70
    assert current.condition == "partly_cloudy"  # weather_code 1
    assert current.is_day is True
    assert current.wind_speed_kmh == 8.0


def test_parse_hourly_starts_at_current_hour_and_is_24():
    hourly = parse_hourly(build_raw())
    # current time is 09:00 → first hourly point is 09:00, and exactly 24 points.
    assert len(hourly) == 24
    assert hourly[0].time == "2026-07-10T09:00"
    assert hourly[0].precipitation_probability_pct == 10


def test_parse_daily_is_seven_days():
    daily = parse_daily(build_raw())
    assert len(daily) == 7
    assert daily[0].temp_max_c == 34.0
    assert daily[0].sunrise == "2026-07-10T05:55"
    assert daily[0].sunset == "2026-07-10T18:35"


def test_parse_location_carries_name():
    location = parse_location(build_raw(), "North Field")
    assert location.latitude == 9.9
    assert location.longitude == 78.1
    assert location.timezone == "Asia/Kolkata"
    assert location.name == "North Field"


def test_parser_tolerates_missing_sections():
    current = parse_current({})
    assert current.temperature_c is None
    assert current.condition == "clear"
    assert parse_hourly({}) == []
    assert parse_daily({}) == []
