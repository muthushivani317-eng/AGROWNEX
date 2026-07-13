"""Unit tests for the pure Soil Engine: Soil Health Card classification, generic
recommendations (no brands, never fabricated) and the notifications collector."""
from __future__ import annotations

from app.modules.notifications.collectors import SoilReportView, collect_soil
from app.modules.soil.engine import (
    SoilValues,
    assess,
    build_recommendations,
    classify_nitrogen,
    classify_ph,
    classify_potassium,
    deficient_micronutrients,
    worst_severity,
)


# --------------------------------------------------------------------------- #
# Classifiers
# --------------------------------------------------------------------------- #
def test_classify_ph_bands() -> None:
    assert classify_ph(None) == "unknown"
    assert classify_ph(5.0) == "strongly_acidic"
    assert classify_ph(6.0) == "acidic"
    assert classify_ph(7.0) == "neutral"
    assert classify_ph(8.0) == "alkaline"
    assert classify_ph(9.0) == "strongly_alkaline"


def test_classify_nutrient_bands() -> None:
    assert classify_nitrogen(200) == "low"
    assert classify_nitrogen(400) == "medium"
    assert classify_nitrogen(600) == "high"
    assert classify_potassium(None) == "unknown"


def test_deficient_micronutrients() -> None:
    assert deficient_micronutrients({"zinc": 0.3, "iron": 10}) == ("zinc",)
    assert deficient_micronutrients(None) == ()


# --------------------------------------------------------------------------- #
# Assessment
# --------------------------------------------------------------------------- #
def test_assess_flags_has_value() -> None:
    assert assess(SoilValues()).has_any_value is False
    assert assess(SoilValues(ph=6.5)).has_any_value is True


# --------------------------------------------------------------------------- #
# Recommendations (generic; never fabricated; no brands)
# --------------------------------------------------------------------------- #
def test_low_nutrients_produce_warnings() -> None:
    recs = build_recommendations(
        SoilValues(ph=5.2, organic_carbon=0.3, nitrogen=200, phosphorus=5, potassium=100)
    )
    codes = {r.code for r in recs}
    assert "soil.rec.ph.strongly_acidic" in codes
    assert "soil.rec.organic_carbon.low" in codes
    assert "soil.rec.nitrogen.low" in codes
    assert "soil.rec.phosphorus.low" in codes
    assert "soil.rec.potassium.low" in codes
    # No commercial brand names anywhere — codes are generic localization keys.
    assert all(r.code.startswith("soil.rec.") for r in recs)


def test_optimal_soil_is_informational() -> None:
    recs = build_recommendations(
        SoilValues(ph=7.0, organic_carbon=1.0, nitrogen=600, phosphorus=30, potassium=300)
    )
    severities = {r.severity for r in recs}
    assert severities <= {"info"}
    assert worst_severity(recs) == "info"


def test_no_data_advises_a_soil_test() -> None:
    recs = build_recommendations(SoilValues())
    assert any(r.code == "soil.rec.general.no_data" for r in recs)


def test_soil_type_baseline_guidance() -> None:
    sandy = build_recommendations(SoilValues(soil_type="Sandy loam"))
    assert any(r.code == "soil.rec.water_holding.sandy" for r in sandy)
    clay = build_recommendations(SoilValues(soil_type="Black clay"))
    assert any(r.code == "soil.rec.drainage.clay" for r in clay)


def test_micronutrient_and_salinity() -> None:
    recs = build_recommendations(
        SoilValues(ec_salinity=3.0, micronutrients={"zinc": 0.2})
    )
    codes = {r.code for r in recs}
    assert "soil.rec.general.salinity_high" in codes
    assert "soil.rec.micronutrient.deficient" in codes
    zinc = next(r for r in recs if r.code == "soil.rec.micronutrient.deficient")
    assert zinc.parameter == "zinc"


def test_worst_severity_none_when_empty() -> None:
    assert worst_severity([]) is None


# --------------------------------------------------------------------------- #
# Notifications collector
# --------------------------------------------------------------------------- #
def test_collect_soil_report_processed_only() -> None:
    events = collect_soil(
        SoilReportView(report_id="r1", farm_id="f1", source="self")
    )
    assert [e.event_type for e in events] == ["report_processed"]


def test_collect_soil_deficiency_alert() -> None:
    events = collect_soil(
        SoilReportView(
            report_id="r1", farm_id="f1", source="soil_health_card",
            has_deficiency=True, deficiency_count=3,
        )
    )
    assert {e.event_type for e in events} == {"report_processed", "deficiency_alert"}
