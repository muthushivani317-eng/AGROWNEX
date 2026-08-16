"""Unit tests for the deterministic weather insight rules (pure)."""
from __future__ import annotations

from app.modules.weather.insights import build_insights
from app.modules.weather.schemas import CurrentWeather, DailyPoint, HourlyPoint


def mk_current(*, temp=30.0, feels=30.0, wind=8.0, precip=0.0) -> CurrentWeather:
    return CurrentWeather(
        time="2026-07-10T09:00",
        temperature_c=temp,
        apparent_temperature_c=feels,
        humidity_pct=70,
        precipitation_mm=precip,
        rain_mm=precip,
        weather_code=1,
        condition="clear",
        is_day=True,
        cloud_cover_pct=10,
        wind_speed_kmh=wind,
        wind_direction_deg=180,
        wind_gusts_kmh=wind + 5,
        uv_index=5.0,
    )


def mk_hourly(*, n=24, prob=10, precip=0.0) -> list[HourlyPoint]:
    return [
        HourlyPoint(
            time=f"h{i}",
            temperature_c=28.0,
            humidity_pct=70,
            precipitation_probability_pct=prob,
            precipitation_mm=precip,
            weather_code=1,
            condition="clear",
            wind_speed_kmh=8.0,
            uv_index=4.0,
            is_day=True,
        )
        for i in range(n)
    ]


def mk_daily(*, tmax=32.0, precip_sum=0.0, prob=10) -> list[DailyPoint]:
    return [
        DailyPoint(
            date=f"d{i}",
            weather_code=1,
            condition="clear",
            temp_max_c=tmax,
            temp_min_c=22.0,
            sunrise="s",
            sunset="e",
            uv_index_max=8.0,
            precipitation_sum_mm=precip_sum,
            precipitation_probability_max_pct=prob,
            wind_speed_max_kmh=12.0,
        )
        for i in range(7)
    ]


def codes(current, hourly, daily) -> set[str]:
    return {i.code for i in build_insights(current, hourly, daily)}


def test_calm_dry_day():
    result = codes(mk_current(), mk_hourly(), mk_daily())
    assert "spraying.good_window" in result
    assert "irrigation.normal" in result
    assert "field_work.favorable" in result
    # No hazard alerts on a calm, mild day.
    assert not {"heat_stress.high", "heat_stress.extreme"} & result
    assert not {"heavy_rain.expected", "heavy_rain.severe"} & result


def test_high_and_extreme_heat():
    high = codes(mk_current(feels=39), mk_hourly(), mk_daily(tmax=41))
    assert "heat_stress.high" in high
    assert "irrigation.recommended" in high  # hot & dry

    extreme = codes(mk_current(feels=43), mk_hourly(), mk_daily(tmax=43))
    assert "heat_stress.extreme" in extreme
    assert "field_work.unfavorable" in extreme


def test_heavy_and_severe_rain():
    heavy = codes(mk_current(), mk_hourly(prob=80, precip=1.0), mk_daily())
    assert "heavy_rain.expected" in heavy
    assert "irrigation.hold" in heavy
    assert "spraying.avoid_rain" in heavy
    assert "field_work.unfavorable" in heavy

    severe = codes(mk_current(), mk_hourly(prob=90, precip=3.0), mk_daily())
    assert "heavy_rain.severe" in severe


def test_wind_rules():
    strong = codes(mk_current(wind=45), mk_hourly(), mk_daily())
    assert "wind.strong" in strong
    assert "spraying.avoid_wind" in strong
    assert "field_work.unfavorable" in strong

    breezy = codes(mk_current(wind=30), mk_hourly(), mk_daily())
    assert "wind.high" in breezy


def test_exactly_one_per_core_category():
    result = build_insights(mk_current(), mk_hourly(), mk_daily())
    cats = [i.category for i in result]
    # Spraying, irrigation and field_work always produce exactly one insight each.
    assert cats.count("spraying") == 1
    assert cats.count("irrigation") == 1
    assert cats.count("field_work") == 1


def test_missing_weather_data_never_creates_a_favorable_action():
    current = mk_current().model_copy(
        update={
            "temperature_c": None,
            "apparent_temperature_c": None,
            "wind_speed_kmh": None,
            "wind_gusts_kmh": None,
            "precipitation_mm": None,
            "rain_mm": None,
        }
    )
    hourly = mk_hourly(prob=None, precip=None)
    for point in hourly:
        point.wind_speed_kmh = None
    daily = mk_daily(tmax=None, precip_sum=None, prob=None)

    result = codes(current, hourly, daily)

    assert "spraying.good_window" not in result
    assert "irrigation.normal" not in result
    assert "field_work.favorable" not in result
