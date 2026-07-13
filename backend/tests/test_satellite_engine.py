"""Unit tests for the pure Satellite Engine + Alert Engine: index calculations,
classification, trend, alerts, and the notifications collector (no database)."""
from __future__ import annotations

from app.modules.notifications.collectors import (
    SatelliteSessionView,
    collect_satellite,
)
from app.modules.satellite.alerts import AlertContext, build_alerts, worst_severity
from app.modules.satellite.engine import (
    BandReflectance,
    IndexValues,
    assess,
    classify_health,
    classify_moisture,
    classify_trend,
    compute_confidence,
    compute_indices,
    index_stats,
)


# --------------------------------------------------------------------------- #
# Index calculations
# --------------------------------------------------------------------------- #
def test_ndvi_and_ndmi_formulas() -> None:
    bands = BandReflectance(red=0.15, nir=0.45, red_edge=0.30, swir=0.25, blue=0.06)
    idx = compute_indices(bands)
    assert idx.ndvi == round((0.45 - 0.15) / (0.45 + 0.15), 4)  # 0.5
    assert idx.ndmi == round((0.45 - 0.25) / (0.45 + 0.25), 4)
    assert idx.ndre == round((0.45 - 0.30) / (0.45 + 0.30), 4)
    assert idx.evi is not None


def test_indices_none_when_bands_missing() -> None:
    idx = compute_indices(BandReflectance(nir=0.4))  # no red / swir / red_edge
    assert idx.ndvi is None
    assert idx.ndmi is None
    assert idx.ndre is None


def test_ratio_guards_divide_by_zero() -> None:
    idx = compute_indices(BandReflectance(red=0.0, nir=0.0))
    assert idx.ndvi is None


def test_index_stats() -> None:
    assert index_stats([]) is None
    mean, mn, mx, std = index_stats([0.4, 0.5, 0.6])
    assert mean == 0.5 and mn == 0.4 and mx == 0.6 and std > 0


# --------------------------------------------------------------------------- #
# Classification + trend
# --------------------------------------------------------------------------- #
def test_health_bands() -> None:
    assert classify_health(None) == "unknown"
    assert classify_health(0.05) == "bare"
    assert classify_health(0.15) == "very_low"
    assert classify_health(0.3) == "low"
    assert classify_health(0.5) == "moderate"
    assert classify_health(0.7) == "good"
    assert classify_health(0.85) == "very_good"


def test_moisture_bands() -> None:
    assert classify_moisture(None) == "unknown"
    assert classify_moisture(-0.3) == "very_dry"
    assert classify_moisture(-0.1) == "dry"
    assert classify_moisture(0.1) == "adequate"
    assert classify_moisture(0.3) == "moist"
    assert classify_moisture(0.5) == "wet"


def test_trend_and_delta() -> None:
    assert classify_trend(0.6, 0.5) == ("improving", 0.1)
    assert classify_trend(0.4, 0.5) == ("declining", -0.1)
    assert classify_trend(0.51, 0.5) == ("stable", 0.01)
    assert classify_trend(0.5, None) == ("unknown", None)


def test_assess_flags_values_and_stress() -> None:
    a = assess(IndexValues(ndvi=0.15, ndmi=0.1))
    assert a.vegetation_health == "very_low"
    assert a.stress_level == "severe"
    assert a.has_values is True
    assert assess(IndexValues()).has_values is False


def test_rapid_drop_raises_stress() -> None:
    # NDVI 0.5 is base 'mild'; a rapid drop (-0.2) raises stress one level → moderate.
    a = assess(IndexValues(ndvi=0.5), previous_ndvi=0.7)
    assert a.trend == "declining"
    assert a.stress_level == "moderate"


def test_confidence_from_cloud_and_sample() -> None:
    assert compute_confidence(0) == 99
    assert compute_confidence(None) == 50
    assert compute_confidence(10, is_sample=True) <= 55


# --------------------------------------------------------------------------- #
# Alert engine
# --------------------------------------------------------------------------- #
def test_missing_imagery_alert_and_no_vegetation() -> None:
    alerts = build_alerts(
        AlertContext(status="unavailable", unavailable_reason="no_imagery")
    )
    assert [a.code for a in alerts] == ["satellite.alert.missing_imagery"]


def test_cloud_obstruction_when_unavailable() -> None:
    alerts = build_alerts(
        AlertContext(status="unavailable", unavailable_reason="cloud_cover", cloud_cover=80)
    )
    assert [a.code for a in alerts] == ["satellite.alert.cloud_obstruction"]


def test_available_scene_vegetation_alerts() -> None:
    alerts = build_alerts(
        AlertContext(
            status="available", ndvi=0.25, ndmi=-0.1, ndvi_delta=-0.25,
            trend="declining", ndvi_std=0.2, cloud_cover=30,
        )
    )
    codes = {a.code for a in alerts}
    assert "satellite.alert.abnormal_seasonal_change" in codes
    assert "satellite.alert.low_vigor" in codes
    assert "satellite.alert.moisture_stress" in codes
    assert "satellite.alert.large_field_variation" in codes
    assert "satellite.alert.cloud_obstruction" in codes  # 30% ≥ advisory
    assert worst_severity(alerts) == "critical"


def test_rapid_ndvi_drop_alert() -> None:
    alerts = build_alerts(
        AlertContext(status="available", ndvi=0.5, ndvi_delta=-0.16)
    )
    assert any(a.code == "satellite.alert.rapid_ndvi_drop" for a in alerts)


def test_early_decline_when_still_healthy() -> None:
    alerts = build_alerts(
        AlertContext(status="available", ndvi=0.55, ndvi_delta=-0.07)
    )
    assert any(a.code == "satellite.alert.early_vegetation_decline" for a in alerts)


def test_healthy_scene_has_no_alerts() -> None:
    alerts = build_alerts(
        AlertContext(status="available", ndvi=0.7, ndmi=0.3, ndvi_delta=0.02, cloud_cover=5)
    )
    assert alerts == []


# --------------------------------------------------------------------------- #
# Notifications collector
# --------------------------------------------------------------------------- #
def test_collect_satellite_events() -> None:
    veg = collect_satellite(
        SatelliteSessionView(session_id="s1", farm_id="f1", has_vegetation_alert=True)
    )
    assert [e.event_type for e in veg] == ["vegetation_decline"]
    unavail = collect_satellite(
        SatelliteSessionView(session_id="s1", farm_id="f1", unavailable=True)
    )
    assert [e.event_type for e in unavail] == ["imagery_unavailable"]
    assert collect_satellite(SatelliteSessionView(session_id="s1", farm_id="f1")) == []
