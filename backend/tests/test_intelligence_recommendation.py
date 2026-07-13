"""Unit tests for the pure Recommendation Engine.

Transparent cross-module prioritization: treat a confident disease before a nutrient
deficiency; vigor decline with healthy leaves → inspect irrigation; heavy-rain +
disease → preventive advisory. Every recommendation is a generic localization code
(no brands) and none is invented when the evidence is absent.
"""
from __future__ import annotations

from app.modules.intelligence.decision import assess_risk, detect_issues
from app.modules.intelligence.engine import compute_health
from app.modules.intelligence.recommendation import (
    MAX_RECOMMENDATIONS,
    generate_recommendations,
)
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


def _recommend(inputs: IntelligenceInputs) -> list:
    scores = compute_health(inputs)
    issues = detect_issues(inputs, scores)
    risk = assess_risk(inputs, scores, issues)
    return generate_recommendations(inputs, scores, issues, risk)


def _codes(drafts) -> set[str]:
    return {d.code for d in drafts}


class TestGenerateRecommendations:
    def test_all_codes_are_generic_no_brands(self) -> None:
        inputs = IntelligenceInputs(
            disease=DiseaseSignal(disease="blast", confidence=90, severity="high"),
        )
        drafts = _recommend(inputs)
        assert drafts
        assert all(d.code.startswith("intelligence.rec.") for d in drafts)

    def test_confident_disease_is_treated_first(self) -> None:
        inputs = IntelligenceInputs(
            disease=DiseaseSignal(disease="blast", confidence=85, severity="high"),
        )
        drafts = _recommend(inputs)
        assert "intelligence.rec.treat_disease" in _codes(drafts)
        assert drafts[0].code == "intelligence.rec.treat_disease"
        assert drafts[0].priority == "high"

    def test_low_soil_nitrogen_prioritizes_nitrogen(self) -> None:
        inputs = IntelligenceInputs(
            soil=SoilSignal(has_data=True, nitrogen="low", phosphorus="medium", potassium="high"),
            nutrient=NutrientSignal(
                primary="nitrogen", status="confirmed", confidence=75, severity="moderate"
            ),
        )
        drafts = _recommend(inputs)
        assert "intelligence.rec.address_nitrogen" in _codes(drafts)

    def test_generic_nutrient_when_not_nitrogen(self) -> None:
        inputs = IntelligenceInputs(
            nutrient=NutrientSignal(
                primary="zinc", status="confirmed", confidence=75, severity="moderate"
            ),
        )
        drafts = _recommend(inputs)
        assert "intelligence.rec.address_nutrient" in _codes(drafts)

    def test_vigor_decline_with_healthy_leaves_checks_irrigation(self) -> None:
        inputs = IntelligenceInputs(
            satellite=SatelliteSignal(
                ndvi=0.3, vegetation_health="low", stress_level="moderate",
                moisture_status="normal", trend="declining",
            ),
        )
        drafts = _recommend(inputs)
        assert "intelligence.rec.check_irrigation" in _codes(drafts)

    def test_heavy_rain_with_disease_gives_preventive_advisory(self) -> None:
        inputs = IntelligenceInputs(
            disease=DiseaseSignal(disease="blast", confidence=70, severity="moderate"),
            weather=WeatherSignal(insight_codes=("heavy_rain.severe",)),
        )
        drafts = _recommend(inputs)
        assert "intelligence.rec.preventive_advisory" in _codes(drafts)

    def test_moisture_stress_without_rain_irrigates(self) -> None:
        inputs = IntelligenceInputs(
            satellite=SatelliteSignal(
                ndvi=0.7, vegetation_health="good", stress_level=None,
                moisture_status="very_dry", trend="stable",
            ),
        )
        drafts = _recommend(inputs)
        assert "intelligence.rec.irrigate" in _codes(drafts)

    def test_missed_tasks_catch_up(self) -> None:
        inputs = IntelligenceInputs(
            weather=WeatherSignal(insight_codes=()),
            calendar=CalendarSignal(missed=2),
        )
        drafts = _recommend(inputs)
        assert "intelligence.rec.catch_up_tasks" in _codes(drafts)

    def test_low_confidence_asks_for_more_data(self) -> None:
        # A single soil module → low coverage → low overall confidence.
        inputs = IntelligenceInputs(
            soil=SoilSignal(has_data=True, nitrogen="high", phosphorus="high", potassium="high"),
        )
        drafts = _recommend(inputs)
        assert "intelligence.rec.gather_more_data" in _codes(drafts)

    def test_high_risk_consults_expert_when_none_open(self) -> None:
        inputs = IntelligenceInputs(
            disease=DiseaseSignal(disease="blast", confidence=90, severity="high"),
            expert=ExpertSignal(open_consultation=False),
        )
        drafts = _recommend(inputs)
        assert "intelligence.rec.consult_expert" in _codes(drafts)
        assert "intelligence.rec.await_expert" not in _codes(drafts)

    def test_high_risk_awaits_open_consultation(self) -> None:
        inputs = IntelligenceInputs(
            disease=DiseaseSignal(disease="blast", confidence=90, severity="high"),
            expert=ExpertSignal(open_consultation=True),
        )
        drafts = _recommend(inputs)
        assert "intelligence.rec.await_expert" in _codes(drafts)
        assert "intelligence.rec.consult_expert" not in _codes(drafts)

    def test_healthy_and_quiet_maintains_routine(self) -> None:
        inputs = IntelligenceInputs(
            weather=WeatherSignal(insight_codes=()),
            growth=GrowthSignal(health_score=92, health_delta=1, risk_level="low"),
            soil=SoilSignal(has_data=True, nitrogen="high", phosphorus="high", potassium="high"),
            satellite=SatelliteSignal(
                ndvi=0.8, vegetation_health="very_good", stress_level=None,
                moisture_status="normal", trend="stable",
            ),
        )
        drafts = _recommend(inputs)
        assert "intelligence.rec.maintain" in _codes(drafts)

    def test_no_evidence_recommends_nothing_invented(self) -> None:
        drafts = _recommend(IntelligenceInputs())
        # Nothing to act on and no data → no fabricated treatment advice.
        assert "intelligence.rec.treat_disease" not in _codes(drafts)
        assert "intelligence.rec.address_nutrient" not in _codes(drafts)

    def test_capped_at_max_recommendations(self) -> None:
        inputs = IntelligenceInputs(
            disease=DiseaseSignal(disease="blast", confidence=90, severity="high"),
            nutrient=NutrientSignal(
                primary="nitrogen", status="confirmed", confidence=80, severity="severe"
            ),
            soil=SoilSignal(has_data=True, nitrogen="low", phosphorus="low", potassium="low",
                            salinity="high"),
            satellite=SatelliteSignal(
                ndvi=0.2, vegetation_health="low", stress_level="severe",
                moisture_status="very_dry", trend="declining",
            ),
            weather=WeatherSignal(insight_codes=("heavy_rain.severe",)),
            calendar=CalendarSignal(missed=5),
            expert=ExpertSignal(open_consultation=False),
        )
        drafts = _recommend(inputs)
        assert len(drafts) <= MAX_RECOMMENDATIONS
        # Sorted by priority — the first is never lower priority than the last.
        priorities = [d.priority for d in drafts]
        order = {"high": 0, "medium": 1, "low": 2}
        assert priorities == sorted(priorities, key=lambda p: order[p])
