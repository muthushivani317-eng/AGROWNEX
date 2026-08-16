from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ReadinessState(StrEnum):
    NOT_ASSESSED = "not_assessed"
    INSUFFICIENT_DATA = "insufficient_data"
    NOT_READY = "not_ready"
    POSSIBLY_READY = "possibly_ready"
    AWAITING_FARMER_CONFIRMATION = "awaiting_farmer_confirmation"
    FARMER_CONFIRMED_READY = "farmer_confirmed_ready"
    FARMER_CONFIRMED_NOT_READY = "farmer_confirmed_not_ready"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    NO_VERIFIED_READINESS_RULE = "no_verified_readiness_rule"


@dataclass(frozen=True)
class ReadinessCriteria:
    crop: str
    version: str
    lifecycle: str
    criteria_hash: str
    required_confirmed_stage: str
    required_observations: tuple[str, ...]
    variety: str | None = None
    region: str | None = None
    season: str | None = None
    source_references: tuple[str, ...] = ()
    reviewer: str | None = None
    approval_date: str | None = None
    expiry_date: str | None = None
    require_fresh_weather: bool = False

    @property
    def active_verified(self) -> bool:
        return (
            self.lifecycle == "verified"
            and len(self.criteria_hash) == 64
            and bool(self.source_references)
            and bool(self.reviewer)
            and bool(self.approval_date)
        )


@dataclass(frozen=True)
class ReadinessEvidence:
    crop: str
    stage: str | None = None
    stage_confirmed: bool = False
    observations: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    weather_freshness: str = "missing"
    planting_date_present: bool = False
    expected_harvest_date_present: bool = False


@dataclass(frozen=True)
class ReadinessAssessment:
    state: ReadinessState
    reliability: str
    evidence_observed: tuple[str, ...]
    missing: tuple[str, ...]
    conflicts: tuple[str, ...]
    criteria_version: str | None
    farmer_confirmation_required: bool


def assess_readiness(
    evidence: ReadinessEvidence, criteria: ReadinessCriteria | None
) -> ReadinessAssessment:
    if criteria is None or not criteria.active_verified or criteria.crop != evidence.crop:
        return ReadinessAssessment(
            ReadinessState.NO_VERIFIED_READINESS_RULE,
            "unavailable",
            evidence.observations,
            ("verified_readiness_criteria",),
            evidence.conflicts,
            criteria.version if criteria else None,
            False,
        )
    if evidence.conflicts:
        return ReadinessAssessment(
            ReadinessState.CONFLICTING_EVIDENCE,
            "conflicting",
            evidence.observations,
            (),
            evidence.conflicts,
            criteria.version,
            False,
        )
    missing = []
    if not evidence.stage_confirmed or evidence.stage != criteria.required_confirmed_stage:
        missing.append("confirmed_required_stage")
    missing.extend(
        item for item in criteria.required_observations if item not in evidence.observations
    )
    if criteria.require_fresh_weather and evidence.weather_freshness != "live":
        missing.append("live_weather")
    if missing:
        return ReadinessAssessment(
            ReadinessState.INSUFFICIENT_DATA,
            "incomplete",
            evidence.observations,
            tuple(missing),
            (),
            criteria.version,
            False,
        )
    return ReadinessAssessment(
        ReadinessState.AWAITING_FARMER_CONFIRMATION,
        "complete_compatible_evidence",
        evidence.observations,
        (),
        (),
        criteria.version,
        True,
    )
