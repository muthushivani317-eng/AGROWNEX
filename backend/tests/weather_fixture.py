"""Shared Open-Meteo-shaped fixture for weather tests (not a test module)."""
from __future__ import annotations

from typing import Any


def build_raw(**current_overrides: Any) -> dict[str, Any]:
    """A realistic Open-Meteo payload; `current_overrides` tweak the `current` block."""
    hourly_times = [f"2026-07-10T{h:02d}:00" for h in range(24)] + [
        f"2026-07-11T{h:02d}:00" for h in range(24)
    ]
    n = len(hourly_times)
    current = {
        "time": "2026-07-10T09:00",
        "temperature_2m": 30.0,
        "apparent_temperature": 32.0,
        "relative_humidity_2m": 70,
        "precipitation": 0.0,
        "rain": 0.0,
        "weather_code": 1,
        "is_day": 1,
        "cloud_cover": 20,
        "wind_speed_10m": 8.0,
        "wind_direction_10m": 180,
        "wind_gusts_10m": 15.0,
        "uv_index": 6.0,
    }
    current.update(current_overrides)
    return {
        "latitude": 9.9,
        "longitude": 78.1,
        "timezone": "Asia/Kolkata",
        "current": current,
        "hourly": {
            "time": hourly_times,
            "temperature_2m": [28.0] * n,
            "relative_humidity_2m": [70] * n,
            "precipitation_probability": [10] * n,
            "precipitation": [0.0] * n,
            "weather_code": [1] * n,
            "wind_speed_10m": [8.0] * n,
            "uv_index": [5.0] * n,
            "is_day": [1 if 6 <= int(t[11:13]) <= 18 else 0 for t in hourly_times],
        },
        "daily": {
            "time": [f"2026-07-{10 + i:02d}" for i in range(7)],
            "weather_code": [1] * 7,
            "temperature_2m_max": [34.0] * 7,
            "temperature_2m_min": [24.0] * 7,
            "sunrise": ["2026-07-10T05:55"] * 7,
            "sunset": ["2026-07-10T18:35"] * 7,
            "uv_index_max": [8.0] * 7,
            "precipitation_sum": [0.0] * 7,
            "precipitation_probability_max": [10] * 7,
            "wind_speed_10m_max": [12.0] * 7,
        },
    }
