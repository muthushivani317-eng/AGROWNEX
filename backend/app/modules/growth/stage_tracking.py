from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class StageState(StrEnum):
    NOT_STARTED = "not_started"
    STAGE_UNKNOWN = "stage_unknown"
    STAGE_SUGGESTED = "stage_suggested"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    CONFIRMED = "confirmed"
    UNCERTAIN = "uncertain"
    CORRECTED = "corrected"
    COMPLETED = "completed"


STAGE_ORDER = [
    "germination",
    "seedling",
    "vegetative",
    "flowering",
    "fruiting",
    "maturity",
    "harvest",
]


class TransitionError(ValueError):
    pass


@dataclass(frozen=True)
class StageEvidence:
    registry_verified: bool = False
    registry_version: str | None = None
    planting_date_present: bool = False
    weather_source: str | None = None
    image_observation: str | None = None
    suggested_stage: str | None = None
    supports: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class StageTransition:
    state: StageState
    suggested_stage: str | None = None
    confirmed_stage: str | None = None
    backward_correction: bool = False
    evidence: StageEvidence = field(default_factory=StageEvidence)


def transition_stage(
    current: StageState | None,
    *,
    event: str,
    evidence: StageEvidence,
    stage: str | None = None,
    prior_stage: str | None = None,
    allow_large_jump: bool = False,
) -> StageTransition:
    if event == "evaluate":
        if not evidence.registry_verified:
            return StageTransition(StageState.STAGE_UNKNOWN, evidence=evidence)
        if not evidence.planting_date_present or evidence.missing or evidence.conflicts:
            return StageTransition(StageState.UNCERTAIN, evidence=evidence)
        if evidence.suggested_stage not in STAGE_ORDER:
            return StageTransition(StageState.STAGE_UNKNOWN, evidence=evidence)
        return StageTransition(
            StageState.AWAITING_CONFIRMATION,
            suggested_stage=evidence.suggested_stage,
            evidence=evidence,
        )
    if event not in {"confirm", "correct", "complete"}:
        raise TransitionError("INVALID_STAGE_EVENT")
    if event == "complete":
        return StageTransition(StageState.COMPLETED, confirmed_stage=prior_stage, evidence=evidence)
    if stage not in STAGE_ORDER:
        raise TransitionError("INVALID_GROWTH_STAGE")
    backward = False
    if prior_stage in STAGE_ORDER:
        delta = STAGE_ORDER.index(stage) - STAGE_ORDER.index(prior_stage)
        backward = delta < 0
        if event == "confirm" and delta > 1 and not allow_large_jump:
            raise TransitionError("LARGE_STAGE_JUMP_REQUIRES_CONFIRMATION")
        if event == "confirm" and backward:
            raise TransitionError("BACKWARD_TRANSITION_REQUIRES_CORRECTION")
    return StageTransition(
        StageState.CORRECTED if event == "correct" else StageState.CONFIRMED,
        confirmed_stage=stage,
        backward_correction=backward,
        evidence=evidence,
    )
