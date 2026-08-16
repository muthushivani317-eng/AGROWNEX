from datetime import UTC, datetime

from app.modules.disease_risk.engine import RiskEvaluation, RiskOutcome
from app.modules.notifications.collectors import collect_disease_risk_conditions


def test_only_conditions_present_creates_distinct_non_diagnostic_event() -> None:
    evaluation = RiskEvaluation(
        RiskOutcome.RISK_CONDITIONS_PRESENT,
        matched_conditions=["humidity_pct:gte"],
        rule_pack_id="pack-1",
        rule_pack_version="1.0.0",
        evaluated_at=datetime.now(UTC),
    )
    events = collect_disease_risk_conditions(
        evaluation, farm_id="farm-1", crop_id="rice", disease_id="blast_risk"
    )
    assert len(events) == 1
    assert events[0].event_type == "disease_risk_conditions"
    assert events[0].event_type != "high_confidence_disease"


def test_unavailable_or_insufficient_never_alerts() -> None:
    for outcome in (RiskOutcome.RULE_PACK_UNAVAILABLE, RiskOutcome.INSUFFICIENT_DATA):
        assert (
            collect_disease_risk_conditions(
                RiskEvaluation(outcome), farm_id="farm-1", crop_id="rice", disease_id="risk"
            )
            == []
        )
