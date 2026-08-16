from datetime import UTC, date, datetime, timedelta

from app.modules.soil.constants import PARAMETER_UNITS
from app.modules.soil.evidence import (
    EvidenceType,
    IndicatorEvidence,
    IndicatorStatus,
    derive_indicator,
)

NOW = datetime(2026, 8, 13, tzinfo=UTC)


def item(**overrides) -> IndicatorEvidence:
    values = dict(
        indicator="ph",
        value=6.8,
        unit="pH",
        evidence_type=EvidenceType.LABORATORY_MEASURED,
        collection_method="laboratory_report",
        collected_at=date(2026, 8, 1),
        source_reference="LAB-1",
        spatial_coverage="sample",
        confidence=95,
        uncertainty_low=None,
        uncertainty_high=None,
        verification_state="verified",
        report_reference="report-1",
    )
    values.update(overrides)
    return IndicatorEvidence(**values)


def test_measured_and_estimated_remain_separate_and_lab_is_selected() -> None:
    lab = item()
    estimate = item(
        value=7.9,
        evidence_type=EvidenceType.REMOTE_SENSING_ESTIMATE,
        source_reference="scene-1",
        report_reference=None,
    )
    result = derive_indicator("ph", [estimate, lab], today=NOW.date())
    assert result.selected == lab
    assert result.measured == [lab]
    assert result.estimated == [estimate]
    assert result.status == IndicatorStatus.CONFLICTING


def test_partial_input_marks_missing_indicators_not_measured() -> None:
    result = derive_indicator("nitrogen", [], today=NOW.date())
    assert result.status == IndicatorStatus.NOT_MEASURED
    assert result.selected is None


def test_stale_evidence_cannot_be_assessed_confidently() -> None:
    result = derive_indicator(
        "ph", [item(collected_at=NOW.date() - timedelta(days=800))], today=NOW.date()
    )
    assert result.status == IndicatorStatus.STALE


def test_uncertainty_and_units_are_preserved() -> None:
    estimate = item(
        evidence_type=EvidenceType.REMOTE_SENSING_ESTIMATE,
        unit="%",
        uncertainty_low=0.3,
        uncertainty_high=0.7,
    )
    result = derive_indicator("ph", [estimate], today=NOW.date())
    assert result.selected and result.selected.unit == "%"
    assert result.selected.uncertainty_low == 0.3
    assert result.selected.uncertainty_high == 0.7


def test_every_numeric_soil_parameter_has_explicit_unit_metadata() -> None:
    assert PARAMETER_UNITS["ph"] == "pH"
    assert all(PARAMETER_UNITS[name] for name in PARAMETER_UNITS)


def test_truth_classes_remain_distinct() -> None:
    assert len(
        {
            EvidenceType.LAB_MEASURED.value,
            EvidenceType.REPORT_EXTRACTED.value,
            EvidenceType.USER_ENTERED.value,
            EvidenceType.REMOTE_ESTIMATE.value,
            EvidenceType.MODEL_ESTIMATE.value,
            EvidenceType.UNAVAILABLE.value,
        }
    ) == 6
