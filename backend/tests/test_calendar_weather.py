"""Unit tests for the read-time weather adjuster (reuses weather insight codes)."""
from __future__ import annotations

from app.modules.calendar.constants import WeatherAdvisory, WeatherDependency
from app.modules.calendar.weather_adjuster import advisory_for, collect_insight_codes
from app.modules.weather.schemas import WeatherInsight


def _insight(code: str) -> WeatherInsight:
    return WeatherInsight(
        code=code, category="c", severity="s", title="t", message="m"
    )


def test_heavy_rain_delays_irrigation():
    codes = {"heavy_rain.severe", "field_work.unfavorable"}
    assert (
        advisory_for(WeatherDependency.IRRIGATION, codes)
        == WeatherAdvisory.DELAY_IRRIGATION
    )


def test_extreme_heat_recommends_irrigation():
    codes = {"heat_stress.extreme"}
    assert (
        advisory_for(WeatherDependency.IRRIGATION, codes)
        == WeatherAdvisory.RECOMMEND_IRRIGATION
    )


def test_heavy_rain_takes_precedence_over_heat_for_irrigation():
    codes = {"heavy_rain.expected", "heat_stress.high"}
    assert (
        advisory_for(WeatherDependency.IRRIGATION, codes)
        == WeatherAdvisory.DELAY_IRRIGATION
    )


def test_strong_wind_delays_spraying():
    codes = {"wind.strong"}
    assert (
        advisory_for(WeatherDependency.SPRAYING, codes)
        == WeatherAdvisory.DELAY_SPRAYING
    )


def test_mild_wind_does_not_delay_spraying():
    assert advisory_for(WeatherDependency.SPRAYING, {"wind.high"}) == WeatherAdvisory.NONE


def test_no_dependency_never_gets_an_advisory():
    codes = {"heavy_rain.severe", "wind.strong", "heat_stress.extreme"}
    assert advisory_for(WeatherDependency.NONE, codes) == WeatherAdvisory.NONE


def test_irrigation_task_ignores_wind():
    assert (
        advisory_for(WeatherDependency.IRRIGATION, {"wind.strong"})
        == WeatherAdvisory.NONE
    )


def test_collect_insight_codes():
    codes = collect_insight_codes([_insight("wind.strong"), _insight("irrigation.normal")])
    assert codes == {"wind.strong", "irrigation.normal"}
