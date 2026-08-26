"""Unit tests for the pure Crop Intelligence Engine (health scoring).

No database, no I/O. Each module contributes a 0-100 sub-score; the overall score is
the weight-normalized average of the sub-scores actually present. Absent modules are
never invented — they lower confidence. Fully deterministic and reproducible.
"""
from __future__ import annotations

from app.modules.intelligence.engine import (
    HealthScores,
    compute_health,
    disease_score,
    growth_score,
    nutrient_score,
    satellite_score,
    soil_score,
    weather_score,
)
from app.modules.intelligence.signals import (
    DiseaseSignal,
    GrowthSignal,
    IntelligenceInputs,
    NutrientSignal,
    SatelliteSignal,
    SoilSignal,
    WeatherSignal,
)


# --------------------------------------------------------------------------- #
# Per-module sub-scores
# --------------------------------------------------------------------------- #
class TestSubScores:
    def test_disease_high_severity_low_score(self) -> None:
        low = disease_score(DiseaseSignal(disease="blast", confidence=90, severity="high"))
        healthy = disease_score(DiseaseSignal(disease=None, confidence=90, severity="none"))
        assert low < 40
        assert healthy == 100
        assert 0 <= low <= 100

    def test_disease_needs_expert_caps_score(self) -> None:
        # A mild finding that still needs an expert is capped at the expert cap.
        capped = disease_score(
            DiseaseSignal(disease="x", confidence=90, severity="low", needs_expert=True)
        )
        assert capped <= 60

    def test_nutrient_not_confirmed_is_a_small_penalty_only(self) -> None:
        # An honest "not confirmed" never crashes the score — never fabricated either.
        s = nutrient_score(
            NutrientSignal(primary=None, status="not_confirmed", confidence=20, severity=None)
        )
        assert s == 88  # 100 - NUTRIENT_NOT_CONFIRMED_PENALTY

    def test_nutrient_confirmed_severe_is_low(self) -> None:
        s = nutrient_score(
            NutrientSignal(primary="nitrogen", status="confirmed", confidence=80, severity="severe")
        )
        assert s <= 40

    def test_nutrient_possible_is_softer_than_confirmed(self) -> None:
        possible = nutrient_score(
            NutrientSignal(
                primary="nitrogen", status="possible", confidence=60, severity="moderate"
            )
        )
        confirmed = nutrient_score(
            NutrientSignal(
                primary="nitrogen", status="confirmed", confidence=60, severity="moderate"
            )
        )
        assert possible > confirmed

    def test_soil_returns_none_without_data(self) -> None:
        assert soil_score(SoilSignal(has_data=False)) is None

    def test_soil_penalizes_low_nutrients_and_salinity(self) -> None:
        healthy = soil_score(
            SoilSignal(has_data=True, nitrogen="high", phosphorus="high", potassium="high")
        )
        poor = soil_score(
            SoilSignal(
                has_data=True,
                nitrogen="low",
                phosphorus="low",
                potassium="low",
                organic_carbon="low",
                salinity="high",
                deficient_micronutrients=("zinc",),
            )
        )
        assert healthy == 100
        assert poor < healthy
        assert poor >= 0

    def test_satellite_from_vegetation_health(self) -> None:
        good = satellite_score(
            SatelliteSignal(ndvi=None, vegetation_health="good", stress_level=None,
                            moisture_status=None, trend=None)
        )
        bare = satellite_score(
            SatelliteSignal(ndvi=None, vegetation_health="bare", stress_level="severe",
                            moisture_status="very_dry", trend="declining")
        )
        assert good > bare
        assert bare < 30

    def test_satellite_falls_back_to_ndvi(self) -> None:
        s = satellite_score(
            SatelliteSignal(ndvi=0.75, vegetation_health=None, stress_level=None,
                            moisture_status=None, trend="improving")
        )
        assert s >= 80

    def test_weather_penalizes_adverse_insights_but_floors_at_40(self) -> None:
        calm = weather_score(WeatherSignal(insight_codes=()))
        storm = weather_score(
            WeatherSignal(
                insight_codes=("heavy_rain.severe", "heat_stress.extreme", "wind.strong"),
                rain_probability_pct=90,
            )
        )
        assert calm == 92
        assert storm < calm
        assert storm >= 40

    def test_growth_uses_health_score_and_delta(self) -> None:
        up = growth_score(GrowthSignal(health_score=70, health_delta=10, risk_level="low"))
        down = growth_score(GrowthSignal(health_score=70, health_delta=-15, risk_level="high"))
        assert up > down

    def test_growth_falls_back_to_risk_level(self) -> None:
        s = growth_score(GrowthSignal(health_score=None, health_delta=None, risk_level="high"))
        assert s == 42


# --------------------------------------------------------------------------- #
# Aggregation
# --------------------------------------------------------------------------- #
class TestComputeHealth:
    def test_no_modules_yields_no_data(self) -> None:
        scores = compute_health(IntelligenceInputs())
        assert isinstance(scores, HealthScores)
        assert scores.overall is None
        assert scores.confidence == 0
        assert scores.has_data is False
        assert scores.sources_used == ()

    def test_single_module_does_not_claim_whole_farm_health(self) -> None:
        inputs = IntelligenceInputs(
            weather=WeatherSignal(insight_codes=())
        )
        scores = compute_health(inputs)
        assert scores.weather == 92
        assert scores.overall is None
        assert scores.sources_used == ("weather",)

    def test_two_independent_modules_can_form_overall_health(self) -> None:
        scores = compute_health(
            IntelligenceInputs(
                weather=WeatherSignal(insight_codes=()),
                growth=GrowthSignal(health_score=80, health_delta=0, risk_level="low"),
            )
        )
        assert scores.overall is not None

    def test_more_modules_raise_confidence(self) -> None:
        one = compute_health(IntelligenceInputs(weather=WeatherSignal(insight_codes=())))
        many = compute_health(
            IntelligenceInputs(
                weather=WeatherSignal(insight_codes=()),
                disease=DiseaseSignal(disease=None, confidence=80, severity="none"),
                growth=GrowthSignal(health_score=80, health_delta=0, risk_level="low"),
                soil=SoilSignal(
                    has_data=True, nitrogen="high", phosphorus="high", potassium="high"
                ),
            )
        )
        assert many.confidence > one.confidence
        assert len(many.sources_used) == 4

    def test_overall_is_weighted_average_of_present_modules(self) -> None:
        inputs = IntelligenceInputs(
            disease=DiseaseSignal(disease="x", confidence=90, severity="high"),  # low
            weather=WeatherSignal(insight_codes=()),  # 92
        )
        scores = compute_health(inputs)
        assert scores.disease is not None and scores.weather == 92
        # Overall lies between the two sub-scores (weighted).
        assert min(scores.disease, scores.weather) <= scores.overall <= max(
            scores.disease, scores.weather
        )

    def test_absent_soil_is_none_never_invented(self) -> None:
        scores = compute_health(
            IntelligenceInputs(weather=WeatherSignal(insight_codes=()))
        )
        assert scores.soil is None
        assert scores.disease is None
        assert scores.nutrient is None
