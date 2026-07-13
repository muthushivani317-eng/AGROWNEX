"""Parse a raw Open-Meteo payload into the weather schema (pure, testable)."""
from __future__ import annotations

from typing import Any

from app.modules.weather.constants import (
    FORECAST_DAYS,
    FORECAST_HOURS,
    condition_for_code,
)
from app.modules.weather.schemas import (
    CurrentWeather,
    DailyPoint,
    HourlyPoint,
    WeatherLocation,
)


def _at(values: Any, index: int) -> Any:
    if isinstance(values, list) and index < len(values):
        return values[index]
    return None


def _int(value: Any) -> int | None:
    return int(value) if value is not None else None


def parse_location(raw: dict[str, Any], name: str | None) -> WeatherLocation:
    return WeatherLocation(
        latitude=float(raw.get("latitude", 0.0)),
        longitude=float(raw.get("longitude", 0.0)),
        timezone=raw.get("timezone"),
        name=name,
    )


def parse_current(raw: dict[str, Any]) -> CurrentWeather:
    c = raw.get("current", {})
    code = _int(c.get("weather_code"))
    return CurrentWeather(
        time=c.get("time", ""),
        temperature_c=c.get("temperature_2m"),
        apparent_temperature_c=c.get("apparent_temperature"),
        humidity_pct=_int(c.get("relative_humidity_2m")),
        precipitation_mm=c.get("precipitation"),
        rain_mm=c.get("rain"),
        weather_code=code,
        condition=condition_for_code(code).value,
        is_day=bool(c.get("is_day", 1)),
        cloud_cover_pct=_int(c.get("cloud_cover")),
        wind_speed_kmh=c.get("wind_speed_10m"),
        wind_direction_deg=_int(c.get("wind_direction_10m")),
        wind_gusts_kmh=c.get("wind_gusts_10m"),
        uv_index=c.get("uv_index"),
    )


def parse_hourly(raw: dict[str, Any]) -> list[HourlyPoint]:
    h = raw.get("hourly", {})
    times = h.get("time", []) or []
    current_time = raw.get("current", {}).get("time")

    start = 0
    if current_time:
        for i, value in enumerate(times):
            if value >= current_time:
                start = i
                break

    points: list[HourlyPoint] = []
    for i in range(start, min(start + FORECAST_HOURS, len(times))):
        code = _int(_at(h.get("weather_code"), i))
        points.append(
            HourlyPoint(
                time=times[i],
                temperature_c=_at(h.get("temperature_2m"), i),
                humidity_pct=_int(_at(h.get("relative_humidity_2m"), i)),
                precipitation_probability_pct=_int(
                    _at(h.get("precipitation_probability"), i)
                ),
                precipitation_mm=_at(h.get("precipitation"), i),
                weather_code=code,
                condition=condition_for_code(code).value,
                wind_speed_kmh=_at(h.get("wind_speed_10m"), i),
                uv_index=_at(h.get("uv_index"), i),
                is_day=bool(_at(h.get("is_day"), i)),
            )
        )
    return points


def parse_daily(raw: dict[str, Any]) -> list[DailyPoint]:
    d = raw.get("daily", {})
    dates = d.get("time", []) or []

    points: list[DailyPoint] = []
    for i in range(min(FORECAST_DAYS, len(dates))):
        code = _int(_at(d.get("weather_code"), i))
        points.append(
            DailyPoint(
                date=dates[i],
                weather_code=code,
                condition=condition_for_code(code).value,
                temp_max_c=_at(d.get("temperature_2m_max"), i),
                temp_min_c=_at(d.get("temperature_2m_min"), i),
                sunrise=_at(d.get("sunrise"), i),
                sunset=_at(d.get("sunset"), i),
                uv_index_max=_at(d.get("uv_index_max"), i),
                precipitation_sum_mm=_at(d.get("precipitation_sum"), i),
                precipitation_probability_max_pct=_int(
                    _at(d.get("precipitation_probability_max"), i)
                ),
                wind_speed_max_kmh=_at(d.get("wind_speed_10m_max"), i),
            )
        )
    return points
