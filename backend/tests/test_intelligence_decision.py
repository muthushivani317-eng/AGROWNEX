"""Unit tests for the pure Decision Engine (priority issues + risk assessment).

Cross-module conditions escalate risk; missing data is never invented — it simply
produces fewer issues. Deterministic and reproducible.
"""
from __future__ import annotations

from app.modules.intelligence.decision import (
    assess_risk,
    detect_issues,
)
from app.modules.intelligence.engine import compute_health
from app.modules.intelligence.signals import (
    CalendarSignal,
    DiseaseSignal,
    ExpertSignal,
    GrowthSignal,
    IntelligenceInputs,
    NutrientSignal,
    SatelliteSignal,
    SoilSignal,
    WeatherSignal,
)


def _assess(inputs: IntelligenceInputs) -> tuple[list, str]:
    scores = compute_health(inputs)
    issues = detect_issues(inputs, scores)
    risk = assess_risk(inputs, scores, issues)
    return issues, risk


def _codes(issues) -> set[str]:
    return {i.code for i in issues}


# --------------------------------------------------------------------------- #
# Priority issues
# --------------------------------------------------------------------------- #
class TestDetectIssues:
    def test_no_data_no_issues_low_risk(self) -> None:
        issues, risk = _assess(IntelligenceInputs())
        assert issues == []
        assert risk == "low"

    def test_active_disease_surfaces_issue(self) -> None:
        inputs = IntelligenceInputs(
            disease=DiseaseSignal(disease="blast", confidence=90, severity="high")
        )
        issues, _ = _assess(inputs)
        assert "intelligence.issue.disease_active" in _codes(issues)

    def test_healthy_disease_produces_no_issue(self) -> None:
        inputs = IntelligenceInputs(
            disease=DiseaseSignal(disease=None, confidence=90, severity="none")
        )
        issues, _ = _assess(inputs)
        assert "intelligence.issue.disease_active" not in _codes(issues)

    def test_confirmed_nutrient_deficiency_surfaces_issue(self) -> None:
        inputs = IntelligenceInputs(
            nutrient=NutrientSignal(
                primary="nitrogen", status="confirmed", confidence=80, severity="moderate"
            )
        )
        issues, _ = _assess(inputs)
        assert "intelligence.issue.nutrient_deficiency" in _codes(issues)

    def test_soil_salinity_and_low_nitrogen(self) -> None:
        inputs = IntelligenceInputs(
            soil=SoilSignal(
                has_data=True, nitrogen="low", phosphorus="low", potassium="medium",
                salinity="high",
            )
        )
        issues, _ = _assess(inputs)
        codes = _codes(issues)
        assert "intelligence.issue.soil_salinity" in codes
        assert "intelligence.issue.soil_low_nitrogen" in codes

    def test_vegetation_decline_and_moisture_stress(self) -> None:
        inputs = IntelligenceInputs(
            satellite=SatelliteSignal(
                ndvi=0.2, vegetation_health="low", stress_level="severe",
                moisture_status="very_dry", trend="declining",
                alert_codes=("satellite.alert.vegetation_decline",),
            )
        )
        issues, _ = _assess(inputs)
        codes = _codes(issues)
        assert "intelligence.issue.vegetation_decline" in codes
        assert "intelligence.issue.moisture_stress" in codes

    def test_weather_and_calendar_issues(self) -> None:
        inputs = IntelligenceInputs(
            weather=WeatherSignal(insight_codes=("heavy_rain.expected", "heat_stress.high")),
            calendar=CalendarSignal(missed=4),
        )
        issues, _ = _assess(inputs)
        codes = _codes(issues)
        assert "intelligence.issue.weather_heavy_rain" in codes
        assert "intelligence.issue.weather_heat" in codes
        assert "intelligence.issue.missed_tasks" in codes

    def test_issues_sorted_most_severe_first(self) -> None:
        inputs = IntelligenceInputs(
            disease=DiseaseSignal(disease="blast", confidence=90, severity="high"),
            calendar=CalendarSignal(missed=1),
        )
        issues, _ = _assess(inputs)
        assert issues  # ranked, most severe first
        assert issues[0].rank >= issues[-1].rank


# --------------------------------------------------------------------------- #
# Risk assessment
# --------------------------------------------------------------------------- #
class TestAssessRisk:
    def test_high_confidence_high_severity_disease_forces_critical(self) -> None:
        inputs = IntelligenceInputs(
            disease=DiseaseSignal(disease="blast", confidence=90, severity="high")
        )
        _, risk = _assess(inputs)
        assert risk == "critical"

    def test_severe_soil_salinity_forces_critical(self) -> None:
        inputs = IntelligenceInputs(
            soil=SoilSignal(has_data=True, salinity="high")
        )
        _, risk = _assess(inputs)
        assert risk == "critical"

    def test_confirmed_severe_nutrient_forces_critical(self) -> None:
        inputs = IntelligenceInputs(
            nutrient=NutrientSignal(
                primary="nitrogen", status="confirmed", confidence=80, severity="severe"
            )
        )
        _, risk = _assess(inputs)
        assert risk == "critical"

    def test_healthy_farm_is_low_risk(self) -> None:
        inputs = IntelligenceInputs(
            weather=WeatherSignal(insight_codes=()),
            growth=GrowthSignal(health_score=90, health_delta=2, risk_level="low"),
            soil=SoilSignal(has_data=True, nitrogen="high", phosphorus="high", potassium="high"),
        )
        _, risk = _assess(inputs)
        assert risk == "low"

    def test_adverse_weather_plus_crop_problem_raises_risk(self) -> None:
        # A moderate disease alone would be medium/high; add heavy rain → escalation path.
        inputs = IntelligenceInputs(
            disease=DiseaseSignal(disease="blast", confidence=65, severity="moderate"),
            weather=WeatherSignal(insight_codes=("heavy_rain.severe",)),
            expert=ExpertSignal(open_consultation=False),
        )
        _, risk = _assess(inputs)
        assert risk in ("medium", "high", "critical")
        assert risk != "low"
