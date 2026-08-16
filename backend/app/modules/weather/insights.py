"""Deterministic, rule-based agricultural insights (docs: AI-ready insights).

Pure functions over parsed weather. No AI at runtime yet — every insight is a
transparent rule, so results are reproducible and safe (docs/AI_PROMPTS.md →
Weather Advisor: use only verified data). The frontend localizes each `code`;
the English `title`/`message` here are for AI context, notifications and logs.
"""
from __future__ import annotations

from typing import Any

from app.modules.weather.constants import (
    HEAT_EXTREME_C,
    HEAT_STRESS_C,
    HEAVY_RAIN_MM_24H,
    IRRIGATION_RAIN_MM_24H,
    IRRIGATION_RAIN_PROB_PCT,
    RAIN_PROB_HIGH_PCT,
    SEVERE_RAIN_MM_24H,
    SPRAY_MAX_RAIN_PROB_PCT,
    SPRAY_MAX_WIND_KMH,
    SPRAY_WINDOW_HOURS,
    WIND_ADVISORY_KMH,
    WIND_WARNING_KMH,
    InsightCategory,
    InsightSeverity,
)
from app.modules.weather.schemas import (
    CurrentWeather,
    DailyPoint,
    HourlyPoint,
    WeatherInsight,
)

# code → (english title, english message template using params)
INSIGHT_TEXT: dict[str, tuple[str, str]] = {
    "heat_stress.high": (
        "High heat",
        "High heat near {temp}°C. Protect crops and irrigate during cooler hours.",
    ),
    "heat_stress.extreme": (
        "Extreme heat",
        "Extreme heat near {temp}°C. Avoid midday field work and irrigate to reduce stress.",
    ),
    "heavy_rain.expected": (
        "Rain expected",
        "About {mm} mm of rain likely in 24h ({prob}% chance). "
        "Hold irrigation and protect low fields.",
    ),
    "heavy_rain.severe": (
        "Heavy rain warning",
        "Heavy rain of {mm} mm expected in 24h. Ensure drainage and delay spraying or harvest.",
    ),
    "wind.high": (
        "Breezy",
        "Winds around {speed} km/h. Avoid spraying to prevent drift.",
    ),
    "wind.strong": (
        "Strong wind",
        "Strong winds around {speed} km/h. Postpone spraying and secure structures.",
    ),
    "spraying.good_window": (
        "Good to spray",
        "Calm and dry now — a good window for spraying.",
    ),
    "spraying.avoid_wind": (
        "Avoid spraying",
        "Winds around {speed} km/h will cause drift. Wait for calmer conditions.",
    ),
    "spraying.avoid_rain": (
        "Avoid spraying",
        "Rain likely soon ({prob}%). Spray may wash off — wait for a dry window.",
    ),
    "irrigation.hold": (
        "Hold irrigation",
        "Rain likely ({prob}%). You can hold irrigation and save water.",
    ),
    "irrigation.recommended": (
        "Irrigate",
        "Hot and dry. Irrigate in the early morning or evening.",
    ),
    "irrigation.normal": (
        "Irrigation normal",
        "No unusual conditions. Irrigate as per your crop schedule.",
    ),
    "field_work.favorable": (
        "Good for field work",
        "Conditions are favourable for field work today.",
    ),
    "field_work.unfavorable": (
        "Limit field work",
        "Rough weather expected. Limit field work and plan indoor tasks.",
    ),
}


def _insight(
    code: str,
    category: InsightCategory,
    severity: InsightSeverity,
    params: dict[str, Any],
) -> WeatherInsight:
    title, template = INSIGHT_TEXT[code]
    return WeatherInsight(
        code=code,
        category=category.value,
        severity=severity.value,
        title=title,
        message=template.format(**params),
        params=params,
    )


def build_insights(
    current: CurrentWeather,
    hourly: list[HourlyPoint],
    daily: list[DailyPoint],
) -> list[WeatherInsight]:
    next24 = hourly[:24]
    has_rain_forecast = bool(next24) and any(
        p.precipitation_mm is not None
        or p.precipitation_probability_pct is not None
        for p in next24
    )
    has_near_term_rain = bool(hourly[:SPRAY_WINDOW_HOURS]) and any(
        p.precipitation_mm is not None
        or p.precipitation_probability_pct is not None
        for p in hourly[:SPRAY_WINDOW_HOURS]
    )
    has_wind = current.wind_speed_kmh is not None
    has_current_rain = current.precipitation_mm is not None
    rain_sum_24 = round(sum(p.precipitation_mm or 0 for p in next24), 1)
    rain_prob_24 = max((p.precipitation_probability_pct or 0 for p in next24), default=0)
    rain_prob_soon = max(
        (p.precipitation_probability_pct or 0 for p in hourly[:SPRAY_WINDOW_HOURS]),
        default=0,
    )
    wind_now = current.wind_speed_kmh or 0.0
    raining_now = (current.precipitation_mm or 0) > 0

    heat_values = [
        v
        for v in (current.apparent_temperature_c, daily[0].temp_max_c if daily else None)
        if v is not None
    ]
    heat_peak = max(heat_values) if heat_values else None

    insights: list[WeatherInsight] = []

    # Heat stress
    if heat_peak is not None and heat_peak >= HEAT_EXTREME_C:
        insights.append(
            _insight(
                "heat_stress.extreme",
                InsightCategory.HEAT_STRESS,
                InsightSeverity.CRITICAL,
                {"temp": round(heat_peak)},
            )
        )
    elif heat_peak is not None and heat_peak >= HEAT_STRESS_C:
        insights.append(
            _insight(
                "heat_stress.high",
                InsightCategory.HEAT_STRESS,
                InsightSeverity.WARNING,
                {"temp": round(heat_peak)},
            )
        )

    # Heavy rain
    if has_rain_forecast and rain_sum_24 >= SEVERE_RAIN_MM_24H:
        insights.append(
            _insight(
                "heavy_rain.severe",
                InsightCategory.HEAVY_RAIN,
                InsightSeverity.CRITICAL,
                {"mm": round(rain_sum_24)},
            )
        )
    elif has_rain_forecast and (
        rain_sum_24 >= HEAVY_RAIN_MM_24H or rain_prob_24 >= RAIN_PROB_HIGH_PCT
    ):
        insights.append(
            _insight(
                "heavy_rain.expected",
                InsightCategory.HEAVY_RAIN,
                InsightSeverity.WARNING,
                {"mm": round(rain_sum_24), "prob": rain_prob_24},
            )
        )

    # Wind
    if has_wind and wind_now >= WIND_WARNING_KMH:
        insights.append(
            _insight(
                "wind.strong",
                InsightCategory.WIND,
                InsightSeverity.WARNING,
                {"speed": round(wind_now)},
            )
        )
    elif has_wind and wind_now >= WIND_ADVISORY_KMH:
        insights.append(
            _insight(
                "wind.high",
                InsightCategory.WIND,
                InsightSeverity.ADVICE,
                {"speed": round(wind_now)},
            )
        )

    # Spraying
    if (
        has_wind
        and has_current_rain
        and has_near_term_rain
        and wind_now <= SPRAY_MAX_WIND_KMH
        and rain_prob_soon <= SPRAY_MAX_RAIN_PROB_PCT
        and not raining_now
    ):
        insights.append(
            _insight(
                "spraying.good_window",
                InsightCategory.SPRAYING,
                InsightSeverity.ADVICE,
                {},
            )
        )
    elif has_wind and wind_now > SPRAY_MAX_WIND_KMH:
        insights.append(
            _insight(
                "spraying.avoid_wind",
                InsightCategory.SPRAYING,
                InsightSeverity.ADVICE,
                {"speed": round(wind_now)},
            )
        )
    elif has_near_term_rain:
        insights.append(
            _insight(
                "spraying.avoid_rain",
                InsightCategory.SPRAYING,
                InsightSeverity.ADVICE,
                {"prob": rain_prob_soon},
            )
        )

    # Irrigation
    if has_rain_forecast and (
        rain_sum_24 >= IRRIGATION_RAIN_MM_24H
        or rain_prob_24 >= IRRIGATION_RAIN_PROB_PCT
    ):
        insights.append(
            _insight(
                "irrigation.hold",
                InsightCategory.IRRIGATION,
                InsightSeverity.ADVICE,
                {"prob": rain_prob_24},
            )
        )
    elif heat_peak is not None and heat_peak >= HEAT_STRESS_C:
        insights.append(
            _insight(
                "irrigation.recommended",
                InsightCategory.IRRIGATION,
                InsightSeverity.ADVICE,
                {},
            )
        )
    elif has_rain_forecast and heat_peak is not None:
        insights.append(
            _insight(
                "irrigation.normal",
                InsightCategory.IRRIGATION,
                InsightSeverity.INFO,
                {},
            )
        )

    # Field work
    rough = (
        rain_sum_24 >= HEAVY_RAIN_MM_24H
        or rain_prob_24 >= RAIN_PROB_HIGH_PCT
        or (heat_peak is not None and heat_peak >= HEAT_EXTREME_C)
        or wind_now >= WIND_WARNING_KMH
    )
    has_field_work_data = has_rain_forecast and has_wind and heat_peak is not None
    if rough or has_field_work_data:
        insights.append(
            _insight(
                "field_work.unfavorable" if rough else "field_work.favorable",
                InsightCategory.FIELD_WORK,
                InsightSeverity.WARNING if rough else InsightSeverity.INFO,
                {},
            )
        )

    return insights
