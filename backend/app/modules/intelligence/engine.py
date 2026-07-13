"""Crop Intelligence Engine — health scoring (docs: HEALTH SCORING).

Pure, deterministic and fully unit-tested. Each module contributes a 0-100 health
sub-score; the overall score is the weight-normalized average of the sub-scores that
are actually present. Absent modules are excluded (never invented) and instead lower
the overall confidence. No AI, no I/O, no side effects.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.modules.intelligence.constants import (
    COVERAGE_WEIGHT,
    DISEASE_SEVERITY_PENALTY,
    GROWTH_RISK_SCORE,
    MODULE_BASE_CONFIDENCE,
    MODULE_CONFIDENCE_WEIGHT,
    MODULE_WEIGHTS,
    NEEDS_EXPERT_CAP,
    NUTRIENT_NOT_CONFIRMED_PENALTY,
    NUTRIENT_SEVERITY_PENALTY,
    VEGETATION_HEALTH_SCORE,
    WEATHER_PENALTY,
    HealthCategory,
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

_H = HealthCategory


def _clamp(value: float, lo: float = 0, hi: float = 100) -> int:
    return int(round(max(lo, min(hi, value))))


# --------------------------------------------------------------------------- #
# Per-module sub-scores (None when the module has no data)
# --------------------------------------------------------------------------- #
def disease_score(sig: DiseaseSignal) -> int:
    base = DISEASE_SEVERITY_PENALTY.get(sig.severity or "moderate", 45)
    conf = sig.confidence if sig.confidence is not None else 60
    score = 100 - base * max(conf, 40) / 100
    if sig.needs_expert:
        score = min(score, NEEDS_EXPERT_CAP)
    return _clamp(score)


def nutrient_score(sig: NutrientSignal) -> int:
    if sig.primary is None or sig.status == "not_confirmed":
        return _clamp(100 - NUTRIENT_NOT_CONFIRMED_PENALTY)
    base = NUTRIENT_SEVERITY_PENALTY.get(sig.severity or "unknown", 25)
    factor = 1.0 if sig.status == "confirmed" else 0.6
    return _clamp(100 - base * factor)


def soil_score(sig: SoilSignal) -> int | None:
    if not sig.has_data:
        return None
    score = 100.0
    for rating, low, medium in (
        (sig.nitrogen, 18, 8),
        (sig.phosphorus, 15, 6),
        (sig.potassium, 15, 6),
    ):
        if rating == "low":
            score -= low
        elif rating == "medium":
            score -= medium
    if sig.organic_carbon == "low":
        score -= 10
    if sig.ph_class in ("strongly_acidic", "strongly_alkaline"):
        score -= 15
    elif sig.ph_class in ("acidic", "alkaline"):
        score -= 8
    if sig.salinity == "high":
        score -= 20
    elif sig.salinity == "medium":
        score -= 10
    score -= 8 * len(sig.deficient_micronutrients)
    return _clamp(score)


def satellite_score(sig: SatelliteSignal) -> int:
    base = VEGETATION_HEALTH_SCORE.get(sig.vegetation_health or "", None)
    if base is None:
        if sig.ndvi is None:
            base = 60
        elif sig.ndvi < 0.2:
            base = 25
        elif sig.ndvi < 0.4:
            base = 48
        elif sig.ndvi < 0.6:
            base = 66
        elif sig.ndvi < 0.8:
            base = 85
        else:
            base = 92
    score = float(base)
    if sig.stress_level == "severe":
        score -= 20
    elif sig.stress_level == "moderate":
        score -= 10
    if sig.trend == "declining":
        score -= 8
    elif sig.trend == "improving":
        score += 5
    if sig.moisture_status == "very_dry":
        score -= 8
    elif sig.moisture_status == "dry":
        score -= 4
    return _clamp(score)


def weather_score(sig: WeatherSignal) -> int:
    score = 92.0
    for code in sig.insight_codes:
        score -= WEATHER_PENALTY.get(code, 0)
    if sig.rain_probability_pct is not None and sig.rain_probability_pct >= 80:
        score -= 5
    return _clamp(score, lo=40)


def growth_score(sig: GrowthSignal) -> int:
    if sig.health_score is not None:
        base = float(sig.health_score)
    else:
        base = float(GROWTH_RISK_SCORE.get(sig.risk_level or "medium", 62))
    if sig.health_delta is not None:
        base += max(-15, min(10, sig.health_delta))
    return _clamp(base)


@dataclass(frozen=True)
class HealthScores:
    disease: int | None
    nutrient: int | None
    soil: int | None
    satellite: int | None
    weather: int | None
    growth: int | None
    overall: int | None
    confidence: int
    sources_used: tuple[str, ...]

    @property
    def has_data(self) -> bool:
        return self.overall is not None


def _module_confidence(inputs: IntelligenceInputs) -> dict[str, int]:
    conf: dict[str, int] = {}
    if inputs.disease is not None:
        conf[_H.DISEASE.value] = inputs.disease.confidence or 60
    if inputs.nutrient is not None:
        conf[_H.NUTRIENT.value] = inputs.nutrient.confidence or 55
    if inputs.soil is not None and inputs.soil.has_data:
        conf[_H.SOIL.value] = inputs.soil.confidence or MODULE_BASE_CONFIDENCE[_H.SOIL.value]
    if inputs.satellite is not None:
        conf[_H.SATELLITE.value] = inputs.satellite.confidence or 70
    if inputs.weather is not None:
        conf[_H.WEATHER.value] = MODULE_BASE_CONFIDENCE[_H.WEATHER.value]
    if inputs.growth is not None:
        conf[_H.GROWTH.value] = MODULE_BASE_CONFIDENCE[_H.GROWTH.value]
    return conf


def compute_health(inputs: IntelligenceInputs) -> HealthScores:
    """Compute per-module sub-scores, the overall score and the confidence (pure)."""
    scores: dict[str, int | None] = {
        _H.DISEASE.value: disease_score(inputs.disease) if inputs.disease else None,
        _H.NUTRIENT.value: nutrient_score(inputs.nutrient) if inputs.nutrient else None,
        _H.SOIL.value: soil_score(inputs.soil) if inputs.soil else None,
        _H.SATELLITE.value: satellite_score(inputs.satellite) if inputs.satellite else None,
        _H.WEATHER.value: weather_score(inputs.weather) if inputs.weather else None,
        _H.GROWTH.value: growth_score(inputs.growth) if inputs.growth else None,
    }
    present = {c: s for c, s in scores.items() if s is not None}

    overall: int | None = None
    if present:
        wsum = sum(MODULE_WEIGHTS[c] for c in present)
        weighted = sum(MODULE_WEIGHTS[c] * s for c, s in present.items())
        overall = _clamp(weighted / wsum)

    module_conf = _module_confidence(inputs)
    coverage = len(present) / len(MODULE_WEIGHTS)
    conf_avg = sum(module_conf.values()) / len(module_conf) if module_conf else 0
    confidence = _clamp(
        COVERAGE_WEIGHT * coverage * 100 + MODULE_CONFIDENCE_WEIGHT * conf_avg
    ) if present else 0

    return HealthScores(
        disease=scores[_H.DISEASE.value],
        nutrient=scores[_H.NUTRIENT.value],
        soil=scores[_H.SOIL.value],
        satellite=scores[_H.SATELLITE.value],
        weather=scores[_H.WEATHER.value],
        growth=scores[_H.GROWTH.value],
        overall=overall,
        confidence=confidence,
        sources_used=tuple(present.keys()),
    )
