"""Tests for the deterministic Today's Farm Mission prioritizer."""
from app.modules.weather.mission import prioritize_mission
from app.modules.weather.schemas import WeatherInsight


def insight(code: str, category: str, severity: str, message: str) -> WeatherInsight:
    return WeatherInsight(
        code=code,
        category=category,
        severity=severity,
        title=code,
        message=message,
    )


def test_rain_risk_outranks_spray_conflict() -> None:
    mission = prioritize_mission(
        [
            insight("spraying.avoid_rain", "spraying", "advice", "Rain may wash spray off."),
            insight("heavy_rain.severe", "heavy_rain", "critical", "60 mm rain is likely."),
        ],
        crop="paddy",
    )

    assert mission.source_insight_code == "heavy_rain.severe"
    assert "paddy" in mission.primary_action
    assert mission.avoid is not None and "spraying" in mission.avoid


def test_heat_risk_outranks_irrigation_advice() -> None:
    mission = prioritize_mission(
        [
            insight("irrigation.recommended", "irrigation", "advice", "Irrigate in cooler hours."),
            insight("heat_stress.extreme", "heat_stress", "critical", "Extreme heat is likely."),
        ],
        crop="cotton",
    )

    assert mission.source_insight_code == "heat_stress.extreme"
    assert "cotton" in mission.primary_action
    assert mission.avoid is not None and "midday" in mission.avoid


def test_no_active_risks_prefers_planned_field_work() -> None:
    mission = prioritize_mission(
        [
            insight("irrigation.normal", "irrigation", "info", "Follow the normal schedule."),
            insight("spraying.good_window", "spraying", "advice", "Conditions are calm and dry."),
            insight("field_work.favorable", "field_work", "info", "Field work is favourable."),
        ],
        crop="groundnut",
    )

    assert mission.source_insight_code == "field_work.favorable"
    assert "groundnut" in mission.primary_action
    assert mission.avoid is None


def test_no_usable_insight_returns_cautious_review_instead_of_action() -> None:
    mission = prioritize_mission([], crop="paddy")

    assert mission.source_insight_code is None
    assert mission.primary_action == "Review today's farm conditions"
    assert "not enough weather data" in mission.reason.lower()
    assert "do not act" in mission.confidence_note.lower()


def test_unknown_insight_returns_cautious_review_instead_of_action() -> None:
    mission = prioritize_mission(
        [insight("unverified.rule", "unknown", "critical", "Unverified advice")],
        crop="paddy",
    )

    assert mission.source_insight_code is None
    assert mission.primary_action == "Review today's farm conditions"
    assert "not enough weather data" in mission.reason.lower()
    assert "do not act" in mission.confidence_note.lower()
