from datetime import UTC, datetime, timedelta

from app.modules.disease_risk.engine import RiskInputs, RiskOutcome, evaluate_risk
from app.modules.disease_risk.registry import RulePackRegistry
from app.modules.disease_risk.schemas import RulePack

NOW = datetime(2026, 8, 13, tzinfo=UTC)


def pack(**changes) -> RulePack:
    raw = {
        "schema_version": "1.0",
        "pack_id": "rice-blast-tn",
        "version": "1.0.0",
        "crop_id": "rice",
        "disease_id": "rice_blast_risk_conditions",
        "regions": ["IN-TN"],
        "seasons": ["kharif"],
        "confirmed_stages": ["vegetative"],
        "required_weather_variables": ["humidity_pct"],
        "observation_window_hours": 24,
        "forecast_window_hours": 48,
        "conditions": [{"variable": "humidity_pct", "operator": "gte", "value": 85}],
        "minimum_data_completeness": 1.0,
        "maximum_weather_age_hours": 3,
        "cached_weather_allowed": False,
        "alert_title_key": "diseaseRisk.conditionsTitle",
        "alert_explanation_key": "diseaseRisk.conditionsExplanation",
        "source_references": ["official:test-reference"],
        "reviewer_id": "expert-1",
        "approval_status": "VERIFIED",
        "approved_at": NOW - timedelta(days=1),
        "review_expires_at": NOW + timedelta(days=30),
        "cooldown_hours": 24,
        "alert_expiry_hours": 12,
    }
    supplied_hash = changes.pop("content_hash", None)
    raw.update(changes)
    candidate = RulePack(**raw, content_hash="0" * 64)
    return candidate.model_copy(update={"content_hash": supplied_hash or candidate.expected_hash()})


def inputs(**changes) -> RiskInputs:
    raw = dict(
        crop_id="rice",
        confirmed_stage="vegetative",
        stage_confirmed=True,
        weather={"humidity_pct": 90},
        weather_source="live",
        weather_observed_at=NOW - timedelta(hours=1),
        region="IN-TN",
        season="kharif",
        evaluated_at=NOW,
    )
    raw.update(changes)
    return RiskInputs(**raw)


def test_no_installed_pack_fails_closed() -> None:
    assert evaluate_risk(None, inputs()).outcome == RiskOutcome.RULE_PACK_UNAVAILABLE


def test_registry_rejects_tampered_expired_suspended_and_unverified() -> None:
    assert RulePackRegistry([pack(content_hash="f" * 64)], now=NOW).active == []
    assert RulePackRegistry([pack(review_expires_at=NOW)], now=NOW).active == []
    assert RulePackRegistry([pack(approval_status="SUSPENDED")], now=NOW).active == []
    assert RulePackRegistry([pack(approval_status="UNVERIFIED")], now=NOW).active == []


def test_stage_must_be_confirmed_and_weather_complete_fresh_live() -> None:
    active = RulePackRegistry([pack()], now=NOW).active[0]
    assert (
        evaluate_risk(active, inputs(stage_confirmed=False)).outcome
        == RiskOutcome.STAGE_UNCONFIRMED
    )
    assert evaluate_risk(active, inputs(weather={})).outcome == RiskOutcome.INSUFFICIENT_DATA
    assert (
        evaluate_risk(active, inputs(weather_source="cached")).outcome
        == RiskOutcome.INSUFFICIENT_DATA
    )
    assert (
        evaluate_risk(active, inputs(weather_observed_at=NOW - timedelta(hours=4))).outcome
        == RiskOutcome.INSUFFICIENT_DATA
    )


def test_matching_and_nonmatching_verified_conditions() -> None:
    active = RulePackRegistry([pack()], now=NOW).active[0]
    assert evaluate_risk(active, inputs()).outcome == RiskOutcome.RISK_CONDITIONS_PRESENT
    assert (
        evaluate_risk(active, inputs(weather={"humidity_pct": 60})).outcome
        == RiskOutcome.CONDITIONS_NOT_MET
    )


def test_wrong_crop_region_or_stage_is_out_of_scope() -> None:
    active = RulePackRegistry([pack()], now=NOW).active[0]
    assert evaluate_risk(active, inputs(crop_id="cotton")).outcome == RiskOutcome.OUT_OF_SCOPE
    assert evaluate_risk(active, inputs(region="IN-KA")).outcome == RiskOutcome.OUT_OF_SCOPE
    assert (
        evaluate_risk(active, inputs(confirmed_stage="flowering")).outcome
        == RiskOutcome.OUT_OF_SCOPE
    )
