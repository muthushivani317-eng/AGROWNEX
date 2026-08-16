import pytest
from app.modules.growth.stage_tracking import (
    StageEvidence,
    StageState,
    TransitionError,
    transition_stage,
)


def test_missing_verified_registry_never_suggests_stage() -> None:
    result = transition_stage(None, event="evaluate", evidence=StageEvidence())
    assert result.state == StageState.STAGE_UNKNOWN
    assert result.suggested_stage is None


def test_verified_suggestion_awaits_farmer_confirmation() -> None:
    evidence = StageEvidence(
        registry_verified=True,
        registry_version="rice-v1",
        planting_date_present=True,
        suggested_stage="vegetative",
        supports=["planting_date_offset"],
    )
    result = transition_stage(None, event="evaluate", evidence=evidence)
    assert result.state == StageState.AWAITING_CONFIRMATION
    assert result.confirmed_stage is None


def test_farmer_confirmation_and_backward_correction_are_explicit() -> None:
    confirmed = transition_stage(
        StageState.AWAITING_CONFIRMATION,
        event="confirm",
        evidence=StageEvidence(suggested_stage="flowering"),
        stage="flowering",
    )
    assert confirmed.state == StageState.CONFIRMED
    corrected = transition_stage(
        confirmed.state,
        event="correct",
        evidence=StageEvidence(),
        stage="vegetative",
        prior_stage="flowering",
    )
    assert corrected.state == StageState.CORRECTED
    assert corrected.backward_correction is True


def test_invalid_forward_jump_requires_explicit_confirmation() -> None:
    with pytest.raises(TransitionError, match="LARGE_STAGE_JUMP_REQUIRES_CONFIRMATION"):
        transition_stage(
            StageState.CONFIRMED,
            event="confirm",
            evidence=StageEvidence(suggested_stage="harvest"),
            stage="harvest",
            prior_stage="seedling",
        )


def test_conflicting_or_missing_critical_inputs_are_uncertain() -> None:
    conflict = transition_stage(
        None,
        event="evaluate",
        evidence=StageEvidence(
            registry_verified=True, planting_date_present=True, conflicts=["weather"]
        ),
    )
    missing = transition_stage(
        None, event="evaluate", evidence=StageEvidence(registry_verified=True)
    )
    assert conflict.state == StageState.UNCERTAIN
    assert missing.state == StageState.UNCERTAIN
