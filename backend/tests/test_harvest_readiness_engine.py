from app.modules.produce.harvest_readiness import (
    ReadinessCriteria,
    ReadinessEvidence,
    ReadinessState,
    assess_readiness,
)


def criteria(**changes):
    values = dict(
        crop="paddy",
        version="v1",
        lifecycle="verified",
        criteria_hash="a" * 64,
        required_confirmed_stage="maturity",
        required_observations=("mature_visual_evidence",),
        source_references=("official-source",),
        reviewer="reviewer-1",
        approval_date="2026-08-13",
    )
    values.update(changes)
    return ReadinessCriteria(**values)


def evidence(**changes):
    values = dict(
        crop="paddy",
        stage="maturity",
        stage_confirmed=True,
        observations=("mature_visual_evidence",),
        weather_freshness="live",
    )
    values.update(changes)
    return ReadinessEvidence(**values)


def test_no_verified_pack_is_insufficient_and_has_no_date() -> None:
    result = assess_readiness(evidence(), None)
    assert result.state == ReadinessState.NO_VERIFIED_READINESS_RULE
    assert not hasattr(result, "harvest_date")


def test_unconfirmed_stage_and_missing_evidence_are_insufficient() -> None:
    assert (
        assess_readiness(evidence(stage_confirmed=False), criteria()).state
        == ReadinessState.INSUFFICIENT_DATA
    )
    assert (
        assess_readiness(evidence(observations=()), criteria()).state
        == ReadinessState.INSUFFICIENT_DATA
    )


def test_conflicts_are_not_averaged() -> None:
    result = assess_readiness(evidence(conflicts=("growth_disagrees",)), criteria())
    assert result.state == ReadinessState.CONFLICTING_EVIDENCE


def test_complete_compatible_evidence_is_only_possibly_ready() -> None:
    result = assess_readiness(evidence(), criteria())
    assert result.state == ReadinessState.AWAITING_FARMER_CONFIRMATION
    assert result.reliability == "complete_compatible_evidence"


def test_stale_weather_blocks_when_pack_requires_fresh_weather() -> None:
    result = assess_readiness(
        evidence(weather_freshness="stale"), criteria(require_fresh_weather=True)
    )
    assert result.state == ReadinessState.INSUFFICIENT_DATA
    assert "live_weather" in result.missing
