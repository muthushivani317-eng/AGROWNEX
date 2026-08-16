"""Rank existing weather insights into one explainable daily farm mission."""

from __future__ import annotations

from app.modules.weather.schemas import WeatherInsight, WeatherMission

PRIORITY: dict[str, int] = {
    "heavy_rain.severe": 100,
    "heat_stress.extreme": 95,
    "heavy_rain.expected": 90,
    "heat_stress.high": 85,
    "wind.strong": 80,
    "spraying.avoid_rain": 75,
    "spraying.avoid_wind": 74,
    "irrigation.hold": 70,
    "irrigation.recommended": 65,
    "wind.high": 60,
    "field_work.unfavorable": 55,
    "field_work.favorable": 20,
    "spraying.good_window": 10,
    "irrigation.normal": 5,
}


def _crop_label(crop: str | None) -> str:
    return crop.strip() if crop and crop.strip() else "your crop"


def _action_for(code: str, crop: str | None) -> str:
    label = _crop_label(crop)
    actions = {
        "heavy_rain.severe": f"Protect {label} fields from heavy rain",
        "heavy_rain.expected": f"Check drainage and hold irrigation for {label}",
        "heat_stress.extreme": f"Protect {label} from extreme heat",
        "heat_stress.high": f"Reduce heat stress on {label}",
        "wind.strong": "Secure the field and postpone spraying",
        "wind.high": "Wait for calmer conditions before spraying",
        "spraying.avoid_rain": "Postpone spraying until a dry window",
        "spraying.avoid_wind": "Postpone spraying until winds ease",
        "irrigation.hold": f"Hold irrigation for {label} today",
        "irrigation.recommended": f"Irrigate {label} during cooler hours",
        "field_work.unfavorable": "Limit outdoor field work today",
        "field_work.favorable": f"Complete planned {label} field work today",
        "spraying.good_window": "Use the current calm, dry field-work window",
        "irrigation.normal": f"Follow the normal irrigation schedule for {label}",
    }
    return actions.get(code, "Review today's farm conditions")


def _avoid_for(code: str) -> str | None:
    avoid = {
        "heavy_rain.severe": "Avoid spraying or harvesting until a safer dry window.",
        "heavy_rain.expected": "Avoid unnecessary irrigation and spraying before rain.",
        "heat_stress.extreme": "Avoid midday field work and midday irrigation.",
        "heat_stress.high": "Avoid working or irrigating during the hottest hours.",
        "wind.strong": "Avoid spraying while strong winds may cause drift.",
        "wind.high": "Avoid spraying until winds ease.",
        "spraying.avoid_rain": "Avoid spraying because likely rain may wash it off.",
        "spraying.avoid_wind": "Avoid spraying because wind may cause drift.",
        "irrigation.hold": "Avoid unnecessary irrigation before likely rain.",
        "field_work.unfavorable": "Avoid non-essential outdoor work in rough conditions.",
    }
    return avoid.get(code)


def prioritize_mission(
    insights: list[WeatherInsight], *, crop: str | None = None
) -> WeatherMission:
    """Choose one mission using transparent severity/time-sensitivity rankings."""
    ranked = sorted(
        (insight for insight in insights if insight.code in PRIORITY),
        key=lambda insight: PRIORITY.get(insight.code, 0),
        reverse=True,
    )
    primary = ranked[0] if ranked else None
    if primary is None:
        return WeatherMission(
            primary_action="Review today's farm conditions",
            reason="There is not enough weather data for a safe action right now.",
            avoid=None,
            secondary_actions=[],
            confidence_note=(
                "Reliability is low. Do not act on this note; check the latest "
                "forecast or ask an agricultural expert."
            ),
            source_insight_code=None,
            crop=crop,
        )

    return WeatherMission(
        primary_action=_action_for(primary.code, crop),
        reason=primary.message,
        avoid=_avoid_for(primary.code),
        secondary_actions=[item.message for item in ranked[1:4]],
        confidence_note=(
            "Today's and tomorrow's guidance has higher confidence and will update "
            "as forecast conditions change."
        ),
        source_insight_code=primary.code,
        crop=crop,
    )
