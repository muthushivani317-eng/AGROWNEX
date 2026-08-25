from datetime import UTC, datetime, timedelta

from app.modules.satellite.waterlogging import (
    WaterloggingDecision,
    WaterloggingEvidence,
    assess_waterlogging,
)

NOW = datetime(2026, 8, 13, tzinfo=UTC)


def evidence(**overrides):
    values = dict(
        observed_at=NOW - timedelta(days=1),
        source="copernicus_sentinel_1",
        scene_id="current",
        baseline_scene_id="baseline",
        coverage_pct=92.0,
        evidence_present=["surface_water_change", "compatible_baseline"],
        evidence_missing=[],
        surface_water_change="increase",
        conflicting=False,
        stale=False,
        quality_usable=True,
        policy_verified=True,
    )
    values.update(overrides)
    return WaterloggingEvidence(**values)


def test_consistent_verified_surface_water_increase_is_cautious_possible() -> None:
    result = assess_waterlogging(evidence())
    assert result.decision == WaterloggingDecision.POSSIBLE_WATERLOGGING
    assert "possible" in result.explanation.lower()


def test_verified_no_surface_water_change_is_clear() -> None:
    result = assess_waterlogging(evidence(surface_water_change="none"))
    assert result.decision == WaterloggingDecision.CLEAR


def test_unverified_rule_never_turns_observation_into_alert() -> None:
    result = assess_waterlogging(evidence(policy_verified=False))
    assert result.decision == WaterloggingDecision.POSSIBLE_WATERLOGGING
    assert result.alert is None


def test_unverified_consistent_no_change_is_a_cautious_clear_screening() -> None:
    result = assess_waterlogging(
        evidence(policy_verified=False, surface_water_change="none")
    )
    assert result.decision == WaterloggingDecision.CLEAR
    assert result.alert is None


def test_conflict_requires_review() -> None:
    result = assess_waterlogging(evidence(conflicting=True))
    assert result.decision == WaterloggingDecision.REVIEW_REQUIRED


def test_missing_evidence_always_insufficient() -> None:
    cases = [
        evidence(baseline_scene_id=None, evidence_missing=["baseline_scene"]),
        evidence(stale=True, evidence_missing=["fresh_observation"]),
        evidence(quality_usable=False, evidence_missing=["usable_coverage"]),
        evidence(scene_id=None, evidence_missing=["current_scene"]),
    ]
    assert all(
        assess_waterlogging(case).decision == WaterloggingDecision.INSUFFICIENT_DATA
        for case in cases
    )


def test_insufficient_data_contains_no_measurement_or_alert() -> None:
    result = assess_waterlogging(None, missing=["provider_credentials"])
    assert result.decision == WaterloggingDecision.INSUFFICIENT_DATA
    assert result.surface_water_change is None
    assert result.alert is None


def test_weather_only_signal_is_cautious_and_never_claims_observed_water() -> None:
    result = assess_waterlogging(
        None,
        missing=["satellite_observation"],
        weather_context={
            "status": "live",
            "heavy_rain_signal": True,
            "source": "open-meteo",
        },
    )
    assert result.decision == WaterloggingDecision.RAINFALL_RISK_ONLY
    assert result.surface_water_change is None
    assert result.alert is None
    assert "satellite confirmation is not available" in result.explanation.lower()


def test_stale_weather_never_becomes_rainfall_risk() -> None:
    result = assess_waterlogging(
        None,
        weather_context={"status": "stale", "heavy_rain_signal": True},
    )
    assert result.decision == WaterloggingDecision.INSUFFICIENT_DATA
