"""Weather response schemas (docs/API_CONTRACT.md → WEATHER MODULE)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class WeatherLocation(BaseModel):
    latitude: float
    longitude: float
    timezone: str | None = None
    name: str | None = None


class CurrentWeather(BaseModel):
    time: str
    temperature_c: float | None
    apparent_temperature_c: float | None
    humidity_pct: int | None
    precipitation_mm: float | None
    rain_mm: float | None
    weather_code: int | None
    condition: str
    is_day: bool
    cloud_cover_pct: int | None
    wind_speed_kmh: float | None
    wind_direction_deg: int | None
    wind_gusts_kmh: float | None
    uv_index: float | None


class HourlyPoint(BaseModel):
    time: str
    temperature_c: float | None
    humidity_pct: int | None
    precipitation_probability_pct: int | None
    precipitation_mm: float | None
    weather_code: int | None
    condition: str
    wind_speed_kmh: float | None
    uv_index: float | None
    is_day: bool


class DailyPoint(BaseModel):
    date: str
    weather_code: int | None
    condition: str
    temp_max_c: float | None
    temp_min_c: float | None
    sunrise: str | None
    sunset: str | None
    uv_index_max: float | None
    precipitation_sum_mm: float | None
    precipitation_probability_max_pct: int | None
    wind_speed_max_kmh: float | None


class WeatherInsight(BaseModel):
    """A deterministic, rule-based agricultural insight (AI/notification ready)."""

    code: str
    category: str
    severity: str
    title: str
    message: str
    params: dict[str, Any] = {}


class ForecastOut(BaseModel):
    hourly: list[HourlyPoint]
    daily: list[DailyPoint]


class AlertsOut(BaseModel):
    insights: list[WeatherInsight]


class WeatherBundle(BaseModel):
    location: WeatherLocation
    current: CurrentWeather
    hourly: list[HourlyPoint]
    daily: list[DailyPoint]
    insights: list[WeatherInsight]
    fetched_at: str
    source: str = "open-meteo"
