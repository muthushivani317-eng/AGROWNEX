from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class EvidenceType(StrEnum):
    LAB_MEASURED = "lab_measured"
    REPORT_EXTRACTED = "report_extracted"
    USER_ENTERED = "user_entered"
    REMOTE_ESTIMATE = "remote_estimate"
    MODEL_ESTIMATE = "model_estimate"
    UNAVAILABLE = "unavailable"
    LABORATORY_MEASURED = "laboratory_measured"
    FIELD_MEASURED = "field_measured"
    GOVERNMENT_RECORD = "government_record"
    FARMER_OBSERVED = "farmer_observed"
    REMOTE_SENSING_ESTIMATE = "remote_sensing_estimate"


class IndicatorStatus(StrEnum):
    ASSESSED = "assessed"
    UNKNOWN = "unknown"
    STALE = "stale"
    CONFLICTING = "conflicting"
    NOT_MEASURED = "not_measured"


@dataclass(frozen=True)
class IndicatorEvidence:
    indicator: str
    value: float | str
    unit: str
    evidence_type: EvidenceType
    collection_method: str
    collected_at: date
    source_reference: str
    spatial_coverage: str
    confidence: int | None
    uncertainty_low: float | None
    uncertainty_high: float | None
    verification_state: str
    report_reference: str | None = None


@dataclass(frozen=True)
class DerivedIndicator:
    indicator: str
    status: IndicatorStatus
    selected: IndicatorEvidence | None
    measured: list[IndicatorEvidence]
    estimated: list[IndicatorEvidence]


_MEASURED = {
    EvidenceType.LAB_MEASURED,
    EvidenceType.REPORT_EXTRACTED,
    EvidenceType.LABORATORY_MEASURED,
    EvidenceType.FIELD_MEASURED,
    EvidenceType.GOVERNMENT_RECORD,
}
_PRECEDENCE = {
    EvidenceType.LAB_MEASURED: 5,
    EvidenceType.REPORT_EXTRACTED: 4,
    EvidenceType.USER_ENTERED: 2,
    EvidenceType.REMOTE_ESTIMATE: 1,
    EvidenceType.MODEL_ESTIMATE: 1,
    EvidenceType.UNAVAILABLE: 0,
    EvidenceType.LABORATORY_MEASURED: 5,
    EvidenceType.FIELD_MEASURED: 4,
    EvidenceType.GOVERNMENT_RECORD: 3,
    EvidenceType.FARMER_OBSERVED: 2,
    EvidenceType.REMOTE_SENSING_ESTIMATE: 1,
}


def derive_indicator(
    indicator: str, observations: list[IndicatorEvidence], *, today: date
) -> DerivedIndicator:
    if not observations:
        return DerivedIndicator(indicator, IndicatorStatus.NOT_MEASURED, None, [], [])
    ordered = sorted(
        observations,
        key=lambda item: (_PRECEDENCE[item.evidence_type], item.collected_at),
        reverse=True,
    )
    selected = ordered[0]
    measured = [item for item in observations if item.evidence_type in _MEASURED]
    estimated = [
        item
        for item in observations
        if item.evidence_type
        in {
            EvidenceType.REMOTE_SENSING_ESTIMATE,
            EvidenceType.REMOTE_ESTIMATE,
            EvidenceType.MODEL_ESTIMATE,
        }
    ]
    stale = (today - selected.collected_at).days > 730
    conflict = any(
        isinstance(item.value, int | float)
        and isinstance(selected.value, int | float)
        and item.unit == selected.unit
        and item.value != selected.value
        for item in observations
        if item is not selected
    )
    status = (
        IndicatorStatus.STALE
        if stale
        else IndicatorStatus.CONFLICTING
        if conflict
        else IndicatorStatus.ASSESSED
    )
    return DerivedIndicator(indicator, status, selected, measured, estimated)
