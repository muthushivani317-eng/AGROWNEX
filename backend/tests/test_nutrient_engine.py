"""Unit tests for the pure Nutrient parser + Analysis Engine.

No database, no I/O — the corroboration logic, confirm/not-confirmed thresholds and
generic recommendations are fully deterministic and reproducible.
"""
from __future__ import annotations

import pytest
from app.modules.nutrient.engine import (
    SatelliteReference,
    SoilReference,
    WeatherReference,
    build_recommendations,
    corroborate,
    worst_severity,
)
from app.modules.nutrient.parser import (
    NutrientObservation,
    ObservationParseError,
    parse_observation,
)


def _obs(
    *,
    primary: str | None = "nitrogen",
    secondary: str | None = None,
    confidence: int = 68,
    severity: str = "moderate",
    symptoms: list[str] | None = None,
) -> NutrientObservation:
    return NutrientObservation(
        plant_present=True,
        reject_reason=None,
        crop="paddy",
        visible_symptoms=symptoms or ["yellowing", "older_leaf_first"],
        primary=primary,
        secondary=secondary,
        visual_confidence=confidence,
        severity=severity,
        affected_area="widespread",
        explanation_tamil="ta",
        explanation_english="en",
    )


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #
class TestParser:
    def test_parses_a_valid_observation(self) -> None:
        obs = parse_observation(
            '{"plant_present": true, "crop": "banana", "primary_deficiency": '
            '"potassium", "secondary_deficiency": "magnesium", "confidence": 72, '
            '"severity": "moderate", "affected_area": "patches", '
            '"visible_symptoms": ["leaf_edge_scorch", "yellowing"]}'
        )
        assert obs.primary == "potassium"
        assert obs.secondary == "magnesium"
        assert obs.visual_confidence == 72
        assert obs.severity == "moderate"
        assert obs.affected_area == "patches"
        assert obs.visible_symptoms == ["leaf_edge_scorch", "yellowing"]

    def test_drops_unknown_nutrient_and_symptom(self) -> None:
        obs = parse_observation(
            '{"plant_present": true, "primary_deficiency": "unobtanium", '
            '"visible_symptoms": ["yellowing", "glowing"], "confidence": 50}'
        )
        assert obs.primary is None  # unknown nutrient is never trusted
        assert obs.visible_symptoms == ["yellowing"]  # unknown symptom dropped

    def test_secondary_equal_to_primary_is_cleared(self) -> None:
        obs = parse_observation(
            '{"plant_present": true, "primary_deficiency": "iron", '
            '"secondary_deficiency": "iron", "confidence": 60}'
        )
        assert obs.primary == "iron"
        assert obs.secondary is None

    def test_not_plant_present(self) -> None:
        obs = parse_observation(
            '{"plant_present": false, "reject_reason": "Building"}'
        )
        assert obs.plant_present is False
        assert obs.reject_reason == "building"
        assert obs.primary is None

    def test_out_of_range_confidence_becomes_zero(self) -> None:
        obs = parse_observation(
            '{"plant_present": true, "primary_deficiency": "zinc", "confidence": 250}'
        )
        assert obs.visual_confidence == 0

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(ObservationParseError):
            parse_observation("not json at all")


# --------------------------------------------------------------------------- #
# Engine — corroboration + status
# --------------------------------------------------------------------------- #
class TestCorroborate:
    def test_no_visual_finding_is_not_confirmed(self) -> None:
        a = corroborate(_obs(primary=None, confidence=20))
        assert a.status == "not_confirmed"
        assert a.primary_deficiency is None
        assert a.needs_test is True

    def test_visual_only_is_possible_not_confirmed(self) -> None:
        a = corroborate(_obs(confidence=68))
        assert a.status == "possible"  # visible signs, no corroboration yet
        assert a.needs_test is True

    def test_low_confidence_visual_is_not_confirmed(self) -> None:
        a = corroborate(_obs(confidence=40))
        assert a.status == "not_confirmed"
        assert a.needs_test is True

    def test_soil_low_nitrogen_confirms(self) -> None:
        soil = SoilReference(has_data=True, macro_ratings={"nitrogen": "low"})
        a = corroborate(_obs(primary="nitrogen", confidence=68), soil=soil)
        assert a.soil_supports is True
        assert a.confidence >= 75
        assert a.status == "confirmed"

    def test_soil_high_nitrogen_contradicts(self) -> None:
        soil = SoilReference(has_data=True, macro_ratings={"nitrogen": "high"})
        a = corroborate(_obs(primary="nitrogen", confidence=68), soil=soil)
        assert a.soil_supports is False  # soil says this nutrient is ample
        assert a.status != "confirmed"

    def test_satellite_low_vigor_corroborates_macro(self) -> None:
        sat = SatelliteReference(has_data=True, vegetation_health="low", low_vigor=True)
        a = corroborate(_obs(primary="nitrogen", confidence=68), satellite=sat)
        assert a.satellite_supports is True
        assert a.status == "confirmed"

    def test_weather_heavy_rain_corroborates_nitrogen(self) -> None:
        weather = WeatherReference(has_data=True, heavy_rain=True)
        a = corroborate(_obs(primary="nitrogen", confidence=68), weather=weather)
        assert a.weather_supports is True
        assert a.status == "confirmed"

    def test_micronutrient_soil_deficiency_confirms(self) -> None:
        soil = SoilReference(has_data=True, deficient_micronutrients=("zinc",))
        a = corroborate(_obs(primary="zinc", confidence=68), soil=soil)
        assert a.soil_supports is True
        assert a.status == "confirmed"
        assert a.needs_test is False

    def test_micronutrient_without_soil_recommends_test(self) -> None:
        a = corroborate(_obs(primary="zinc", confidence=68))
        assert a.status == "possible"
        assert a.needs_test is True  # can't corroborate a micronutrient from a photo

    def test_disease_conflict_lowers_confidence_and_asks_expert(self) -> None:
        a = corroborate(_obs(primary="nitrogen", confidence=68), disease_conflict=True)
        assert a.disease_conflict is True
        assert a.needs_expert is True
        assert a.status == "not_confirmed"  # 68 - 20 = 48

    def test_severe_severity_asks_expert(self) -> None:
        soil = SoilReference(has_data=True, macro_ratings={"nitrogen": "low"})
        a = corroborate(_obs(primary="nitrogen", confidence=70, severity="severe"), soil=soil)
        assert a.needs_expert is True

    def test_confidence_never_reaches_certainty(self) -> None:
        soil = SoilReference(has_data=True, macro_ratings={"nitrogen": "low"})
        a = corroborate(_obs(primary="nitrogen", confidence=99), soil=soil)
        assert a.confidence <= 99


# --------------------------------------------------------------------------- #
# Engine — generic recommendations (no brands, never fabricated)
# --------------------------------------------------------------------------- #
class TestRecommendations:
    def test_confirmed_gives_generic_nutrient_advice(self) -> None:
        soil = SoilReference(has_data=True, macro_ratings={"nitrogen": "low"})
        a = corroborate(_obs(primary="nitrogen", confidence=68), soil=soil)
        codes = [r.code for r in build_recommendations(a)]
        assert "nutrient.rec.nitrogen.deficiency" in codes
        # Every recommendation is a generic localization code — never a brand.
        assert all(r.code.startswith("nutrient.rec.") for r in build_recommendations(a))

    def test_secondary_deficiency_is_included(self) -> None:
        soil = SoilReference(has_data=True, macro_ratings={"nitrogen": "low"})
        a = corroborate(
            _obs(primary="nitrogen", secondary="magnesium", confidence=68), soil=soil
        )
        codes = [r.code for r in build_recommendations(a)]
        assert "nutrient.rec.magnesium.deficiency" in codes

    def test_not_confirmed_advises_a_soil_test(self) -> None:
        a = corroborate(_obs(primary=None, confidence=20))
        codes = [r.code for r in build_recommendations(a)]
        assert "nutrient.rec.general.not_confirmed" in codes
        assert "nutrient.rec.test.soil_test" in codes

    def test_expert_recommended_on_conflict(self) -> None:
        a = corroborate(_obs(primary="nitrogen", confidence=68), disease_conflict=True)
        codes = [r.code for r in build_recommendations(a)]
        assert "nutrient.rec.expert.consult" in codes

    def test_worst_severity(self) -> None:
        soil = SoilReference(has_data=True, macro_ratings={"nitrogen": "low"})
        a = corroborate(_obs(primary="nitrogen", confidence=68, severity="severe"), soil=soil)
        assert worst_severity(build_recommendations(a)) in ("warning", "critical")
        assert worst_severity([]) is None
