"""Weather module constants (docs/PRODUCT_RULES.md → Open-Meteo)."""
from __future__ import annotations

import os
from enum import StrEnum

# --- Open-Meteo (docs/PRODUCT_RULES.md rule 5: weather comes from Open-Meteo) ---
OPEN_METEO_BASE_URL = os.getenv(
    "OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1"
)
OPEN_METEO_TIMEOUT_SECONDS = float(os.getenv("OPEN_METEO_TIMEOUT_SECONDS", "8"))
OPEN_METEO_MAX_RETRIES = int(os.getenv("OPEN_METEO_MAX_RETRIES", "3"))

FORECAST_DAYS = 7
FORECAST_HOURS = 24

CURRENT_FIELDS = (
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "is_day",
    "precipitation",
    "rain",
    "weather_code",
    "cloud_cover",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "uv_index",
)
HOURLY_FIELDS = (
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation_probability",
    "precipitation",
    "weather_code",
    "wind_speed_10m",
    "uv_index",
    "is_day",
)
DAILY_FIELDS = (
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "sunrise",
    "sunset",
    "uv_index_max",
    "precipitation_sum",
    "precipitation_probability_max",
    "wind_speed_10m_max",
)

# --- Cache (docs/API_CONTRACT.md → CACHING: weather 5 minutes) ---
WEATHER_CACHE_TTL_SECONDS = int(os.getenv("WEATHER_CACHE_TTL_SECONDS", "300"))
# Coordinates are rounded to ~1 km before caching so nearby requests share entries.
CACHE_COORD_PRECISION = 2


class Condition(StrEnum):
    """Coarse weather category derived from the WMO weather code."""

    CLEAR = "clear"
    PARTLY_CLOUDY = "partly_cloudy"
    CLOUDY = "cloudy"
    FOG = "fog"
    DRIZZLE = "drizzle"
    RAIN = "rain"
    SNOW = "snow"
    THUNDERSTORM = "thunderstorm"


# WMO weather code → coarse condition (open-meteo.com/en/docs → weather codes).
def condition_for_code(code: int | None) -> Condition:
    if code is None:
        return Condition.CLEAR
    if code == 0:
        return Condition.CLEAR
    if code in (1, 2):
        return Condition.PARTLY_CLOUDY
    if code == 3:
        return Condition.CLOUDY
    if code in (45, 48):
        return Condition.FOG
    if code in (51, 53, 55, 56, 57):
        return Condition.DRIZZLE
    if code in (61, 63, 65, 66, 67, 80, 81, 82):
        return Condition.RAIN
    if code in (71, 73, 75, 77, 85, 86):
        return Condition.SNOW
    if code in (95, 96, 99):
        return Condition.THUNDERSTORM
    return Condition.CLOUDY


class InsightCategory(StrEnum):
    IRRIGATION = "irrigation"
    SPRAYING = "spraying"
    HEAT_STRESS = "heat_stress"
    HEAVY_RAIN = "heavy_rain"
    WIND = "wind"
    FIELD_WORK = "field_work"


class InsightSeverity(StrEnum):
    INFO = "info"
    ADVICE = "advice"
    WARNING = "warning"
    CRITICAL = "critical"


# --- Rule thresholds (deterministic agronomic defaults) ---
HEAT_STRESS_C = 38.0
HEAT_EXTREME_C = 42.0
HEAVY_RAIN_MM_24H = 20.0
SEVERE_RAIN_MM_24H = 50.0
RAIN_PROB_HIGH_PCT = 70
WIND_ADVISORY_KMH = 25.0
WIND_WARNING_KMH = 40.0
# Spraying is only advisable in calm, dry conditions.
SPRAY_MAX_WIND_KMH = 15.0
SPRAY_MAX_RAIN_PROB_PCT = 30
SPRAY_WINDOW_HOURS = 6
# Irrigation guidance windows.
IRRIGATION_RAIN_MM_24H = 10.0
IRRIGATION_RAIN_PROB_PCT = 60
