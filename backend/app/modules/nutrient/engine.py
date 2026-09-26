"""Nutrient Analysis Engine (docs: Repository → Service → Engine → Provider).

Pure, deterministic and fully unit-tested. It takes a *visual* observation from the
analysis provider and corroborates it with the Soil, Satellite and Weather signals
(built by the service from those modules' own repositories — no source module is
modified). It then decides a transparent status:

    confirmed      strong visual finding + at least one corroborating signal
    possible       visible signs, not yet corroborated
    not_confirmed  insufficient evidence — recommend a soil / tissue test

It never fabricates a deficiency and never overrides another module's diagnosis
without evidence (a recent high-confidence disease lowers confidence and asks for an
expert). All recommendations are *generic* localization codes — no brands, no AI.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.nutrient.constants import (
    CONFIDENCE_CONFIRM,
    CONFIDENCE_MAX,
    CONFIDENCE_MIN,
    CONFIDENCE_POSSIBLE,
    CONTRADICTION_PENALTY,
    CORROBORATION_BOOST,
    DISEASE_CONFLICT_PENALTY,
    MACRO_NUTRIENTS,
    SEVERITY_ORDER,
    SOIL_MACRO_PARAM,
    SOIL_MICRO_ELEMENTS,
    STRONG_SOIL_BOOST,
    AffectedArea,
    DeficiencyStatus,
    Nutrient,
    Priority,
    RecommendationCategory,
    Severity,
)
from app.modules.nutrient.parser import NutrientObservation

# Recommendation severities (shared vocabulary with the other engines).
_REC_INFO = "info"
_REC_ADVICE = "advice"
_REC_WARNING = "warning"
_REC_CRITICAL = "critical"

_REC_SEVERITY_ORDER = {_REC_INFO: 0, _REC_ADVICE: 1, _REC_WARNING: 2, _REC_CRITICAL: 3}

# Visual severity → recommendation severity.
_SEVERITY_TO_REC: dict[str, str] = {
    Severity.NONE.value: _REC_INFO,
    Severity.MILD.value: _REC_ADVICE,
    Severity.MODERATE.value: _REC_WARNING,
    Severity.SEVERE.value: _REC_CRITICAL,
    Severity.UNKNOWN.value: _REC_ADVICE,
}


# --------------------------------------------------------------------------- #
# Reference inputs (pure views the service builds from the other modules)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class SoilReference:
    """A pure view of the Soil Engine's assessment for the farm."""

    has_data: bool = False
    # nutrient → rating ('low' | 'medium' | 'high' | 'unknown')
    macro_ratings: dict[str, str] = field(default_factory=dict)
    deficient_micronutrients: tuple[str, ...] = ()


@dataclass(frozen=True)
class SatelliteReference:
    """A pure view of the latest available satellite session for the farm."""

    has_data: bool = False
    vegetation_health: str | None = None
    low_vigor: bool = False


@dataclass(frozen=True)
class WeatherReference:
    """A pure view of the current weather insight codes for the farm."""

    has_data: bool = False
    heavy_rain: bool = False
    codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class RecommendationDraft:
    """A generic agronomic recommendation (localization code; no brand)."""

    category: str
    code: str
    severity: str
    priority: str
    nutrient: str | None = None


@dataclass(frozen=True)
class NutrientAssessment:
    """The engine's transparent verdict for one analysed image."""

    primary_deficiency: str | None
    secondary_deficiency: str | None
    status: str
    confidence: int
    severity: str
    affected_area: str | None
    soil_supports: bool | None
    satellite_supports: bool
    weather_supports: bool
    disease_conflict: bool
    needs_test: bool
    needs_expert: bool


def _priority_for(rec_severity: str) -> str:
    if rec_severity == _REC_CRITICAL:
        return Priority.HIGH.value
    if rec_severity == _REC_WARNING:
        return Priority.MEDIUM.value
    return Priority.LOW.value


def _clamp(value: int) -> int:
    return max(CONFIDENCE_MIN, min(CONFIDENCE_MAX, value))


def soil_signal(primary: str, soil: SoilReference) -> tuple[int, bool | None]:
    """(confidence delta, soil_supports) from the soil assessment for ``primary``.

    Public (not ``_``-prefixed) so ``app.modules.nutrient.schemas`` can reuse
    this exact logic when rebuilding a *stored* report's safe result for the
    API, instead of re-deriving it -- a second, incomplete reimplementation
    here (checking only ``macro_ratings``, never ``deficient_micronutrients``)
    is what previously caused soil-confirmed micronutrient deficiencies to
    come back over the API as "abstained" / "not confirmed" even though the
    engine had genuinely corroborated them at analysis time (found in the
    2026-08 pre-release audit).
    """
    if not soil.has_data:
        return 0, None
    if primary in SOIL_MACRO_PARAM:
        rating = soil.macro_ratings.get(SOIL_MACRO_PARAM[primary], "unknown")
        if rating == "low":
            return STRONG_SOIL_BOOST, True
        if rating == "medium":
            return CORROBORATION_BOOST, True
        if rating == "high":
            return -CONTRADICTION_PENALTY, False  # soil says this nutrient is ample
        return 0, None
    if primary in SOIL_MICRO_ELEMENTS:
        if primary in soil.deficient_micronutrients:
            return STRONG_SOIL_BOOST, True
        return 0, None  # absence of a measurement is not proof of sufficiency
    return 0, None


def corroborate(
    observation: NutrientObservation,
    *,
    soil: SoilReference | None = None,
    satellite: SatelliteReference | None = None,
    weather: WeatherReference | None = None,
    disease_conflict: bool = False,
) -> NutrientAssessment:
    """Combine the visual observation with the other modules' signals (pure)."""
    soil = soil or SoilReference()
    satellite = satellite or SatelliteReference()
    weather = weather or WeatherReference()

    primary = observation.primary
    severity = observation.severity
    area = observation.affected_area

    # No conclusive visual finding → honest "not confirmed" (never invented).
    if primary is None:
        return NutrientAssessment(
            primary_deficiency=None,
            secondary_deficiency=None,
            status=DeficiencyStatus.NOT_CONFIRMED.value,
            confidence=_clamp(observation.visual_confidence),
            severity=severity,
            affected_area=area,
            soil_supports=None,
            satellite_supports=False,
            weather_supports=False,
            disease_conflict=disease_conflict,
            needs_test=True,
            needs_expert=disease_conflict,
        )

    confidence = observation.visual_confidence

    soil_delta, soil_supports = soil_signal(primary, soil)
    confidence += soil_delta

    # Satellite: a macro-nutrient shortfall depresses canopy greenness.
    satellite_supports = False
    if satellite.has_data and primary in MACRO_NUTRIENTS and satellite.low_vigor:
        confidence += CORROBORATION_BOOST
        satellite_supports = True

    # Weather: heavy rain leaches mobile nitrogen (context, not proof).
    weather_supports = False
    if weather.has_data and weather.heavy_rain and primary == Nutrient.NITROGEN.value:
        confidence += CORROBORATION_BOOST
        weather_supports = True

    # Never override another module without evidence — a recent high-confidence
    # disease on this farm lowers certainty and asks for an expert.
    if disease_conflict:
        confidence -= DISEASE_CONFLICT_PENALTY

    confidence = _clamp(confidence)
    corroborated = bool(soil_supports) or satellite_supports or weather_supports

    if confidence >= CONFIDENCE_CONFIRM and corroborated:
        status = DeficiencyStatus.CONFIRMED.value
    elif confidence >= CONFIDENCE_POSSIBLE:
        status = DeficiencyStatus.POSSIBLE.value
    else:
        status = DeficiencyStatus.NOT_CONFIRMED.value

    micronutrient_without_soil = primary in SOIL_MICRO_ELEMENTS and not soil.has_data
    needs_test = status != DeficiencyStatus.CONFIRMED.value or micronutrient_without_soil
    needs_expert = disease_conflict or severity == Severity.SEVERE.value

    return NutrientAssessment(
        primary_deficiency=primary,
        secondary_deficiency=observation.secondary,
        status=status,
        confidence=confidence,
        severity=severity if severity != Severity.UNKNOWN.value else Severity.MODERATE.value,
        affected_area=area if area != AffectedArea.UNKNOWN.value else None,
        soil_supports=soil_supports,
        satellite_supports=satellite_supports,
        weather_supports=weather_supports,
        disease_conflict=disease_conflict,
        needs_test=needs_test,
        needs_expert=needs_expert,
    )


def _rec(
    category: RecommendationCategory,
    code: str,
    severity: str,
    *,
    nutrient: str | None = None,
) -> RecommendationDraft:
    return RecommendationDraft(
        category=category.value,
        code=code,
        severity=severity,
        priority=_priority_for(severity),
        nutrient=nutrient,
    )


def build_recommendations(assessment: NutrientAssessment) -> list[RecommendationDraft]:
    """Generic agronomic advice from the assessment (pure, codes only, no brands)."""
    recs: list[RecommendationDraft] = []
    status = assessment.status
    primary = assessment.primary_deficiency

    # A confirmed or clearly visible (possible) deficiency gets its remedy --
    # organic first, then chemical -- as long as nothing contradicts it (soil
    # measuring the nutrient as ample, or a recent disease on the farm). A
    # possible finding also gets the soil-test recommendation below.
    if (
        primary
        and status in (DeficiencyStatus.CONFIRMED.value, DeficiencyStatus.POSSIBLE.value)
        and assessment.soil_supports is not False
        and not assessment.disease_conflict
    ):
        rec_sev = _SEVERITY_TO_REC.get(assessment.severity, _REC_WARNING)
        recs.append(
            _rec(
                RecommendationCategory.NUTRIENT,
                f"nutrient.rec.{primary}.deficiency",
                rec_sev,
                nutrient=primary,
            )
        )

    if status == DeficiencyStatus.NOT_CONFIRMED.value:
        recs.append(
            _rec(
                RecommendationCategory.GENERAL,
                "nutrient.rec.general.not_confirmed",
                _REC_INFO,
            )
        )

    if assessment.needs_test:
        recs.append(_rec(RecommendationCategory.TEST, "nutrient.rec.test.soil_test", _REC_WARNING))

    if assessment.needs_expert:
        recs.append(
            _rec(RecommendationCategory.EXPERT, "nutrient.rec.expert.consult", _REC_WARNING)
        )

    if status == DeficiencyStatus.CONFIRMED.value and assessment.severity in (
        Severity.NONE.value,
        Severity.MILD.value,
    ):
        recs.append(_rec(RecommendationCategory.MONITOR, "nutrient.rec.monitor.observe", _REC_INFO))

    return recs


def worst_severity(recs: list[RecommendationDraft]) -> str | None:
    """The highest-severity recommendation present (for alerts). ``None`` if empty."""
    if not recs:
        return None
    return max(recs, key=lambda r: _REC_SEVERITY_ORDER.get(r.severity, 0)).severity


def deficiency_severity_rank(severity: str) -> int:
    """Rank a visual severity (for choosing the worst across a report)."""
    return SEVERITY_ORDER.get(severity, 0)
