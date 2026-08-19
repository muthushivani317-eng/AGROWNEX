"""Soil Engine (docs: Repository → Service → Soil Engine → Provider).

Pure, deterministic and fully unit-tested. It classifies soil values against the
standard Soil Health Card rating bands and emits *generic* agronomic advice — never
a commercial fertilizer brand, never a fabricated value (docs/PRODUCT_RULES.md).
Each recommendation is a localization ``code`` (+ the measured value) so the
Tamil-first client renders the wording. No AI, no I/O, no side effects.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.farms.constants import SoilType
from app.modules.soil.constants import (
    EC_HIGH,
    EC_NORMAL,
    K_LOW,
    K_MEDIUM,
    MICRONUTRIENT_FLOORS,
    N_LOW,
    N_MEDIUM,
    OC_LOW,
    OC_MEDIUM,
    P_LOW,
    P_MEDIUM,
    PARAMETER_UNITS,
    PH_ACIDIC,
    PH_NEUTRAL_MAX,
    PH_STRONGLY_ACIDIC,
    PH_STRONGLY_ALKALINE,
    DrainageClass,
    PhClass,
    Priority,
    RatingLevel,
    RecommendationCategory,
    Severity,
)

_C = RecommendationCategory
_S = Severity
_R = RatingLevel


@dataclass(frozen=True)
class SoilValues:
    """The pure inputs the engine reasons about (any may be ``None``)."""

    ph: float | None = None
    organic_carbon: float | None = None
    nitrogen: float | None = None
    phosphorus: float | None = None
    potassium: float | None = None
    ec_salinity: float | None = None
    water_holding_capacity: float | None = None
    drainage: str | None = None
    micronutrients: dict[str, float] | None = None
    soil_type: str | None = None


@dataclass(frozen=True)
class RecommendationDraft:
    """A generic agronomic recommendation (localization code + measured value)."""

    category: str
    code: str
    severity: str
    priority: str
    parameter: str | None = None
    rating: str | None = None
    value: float | None = None
    unit: str | None = None


@dataclass(frozen=True)
class SoilAssessment:
    """Per-parameter rating (``unknown`` when the value is unavailable)."""

    ph_class: str
    organic_carbon: str
    nitrogen: str
    phosphorus: str
    potassium: str
    salinity: str
    deficient_micronutrients: tuple[str, ...] = field(default_factory=tuple)
    has_any_value: bool = False


def _priority_for(severity: str) -> str:
    if severity == _S.CRITICAL.value:
        return Priority.HIGH.value
    if severity == _S.WARNING.value:
        return Priority.MEDIUM.value
    return Priority.LOW.value


# --------------------------------------------------------------------------- #
# Classifiers (pure)
# --------------------------------------------------------------------------- #
def classify_ph(ph: float | None) -> str:
    if ph is None:
        return PhClass.UNKNOWN.value
    if ph < PH_STRONGLY_ACIDIC:
        return PhClass.STRONGLY_ACIDIC.value
    if ph < PH_ACIDIC:
        return PhClass.ACIDIC.value
    if ph <= PH_NEUTRAL_MAX:
        return PhClass.NEUTRAL.value
    if ph <= PH_STRONGLY_ALKALINE:
        return PhClass.ALKALINE.value
    return PhClass.STRONGLY_ALKALINE.value


def _band(value: float | None, low: float, medium: float) -> str:
    if value is None:
        return _R.UNKNOWN.value
    if value < low:
        return _R.LOW.value
    if value < medium:
        return _R.MEDIUM.value
    return _R.HIGH.value


def classify_organic_carbon(v: float | None) -> str:
    return _band(v, OC_LOW, OC_MEDIUM)


def classify_nitrogen(v: float | None) -> str:
    return _band(v, N_LOW, N_MEDIUM)


def classify_phosphorus(v: float | None) -> str:
    return _band(v, P_LOW, P_MEDIUM)


def classify_potassium(v: float | None) -> str:
    return _band(v, K_LOW, K_MEDIUM)


def classify_salinity(ec: float | None) -> str:
    if ec is None:
        return _R.UNKNOWN.value
    if ec < EC_NORMAL:
        return _R.OPTIMAL.value
    if ec < EC_HIGH:
        return _R.MEDIUM.value
    return _R.HIGH.value


def classify_texture_bucket(
    clay_pct: float | None, sand_pct: float | None, silt_pct: float | None
) -> str | None:
    """Coarse texture bucket from a clay/sand/silt composition (e.g. SoilGrids'
    remote estimate), returned in this app's own farmer-registered ``SoilType``
    vocabulary (sandy / clay / loamy / silt --
    app.modules.farms.constants.SoilType) rather than a separate 12-class USDA
    soil-texture-triangle taxonomy, so a remote estimate and a farmer's own
    registered soil type are always directly comparable.

    Deliberately conservative: the standard USDA texture triangle has
    non-linear class boundaries this function does not attempt to reproduce
    precisely (unlike the simple numeric bands used for pH/EC above). Instead
    it only classifies into a "pure" bucket when the composition sits well
    inside that corner of the triangle -- clay >= 40% for Clay, silt >= 80%
    (with low clay) for Silt, sand >= 70% (with low clay) for Sand, all comfortably
    inside the true boundary regardless of small uncertainty in the exact
    edges. Every blended composition, and any case this function is unsure
    about, falls to "loamy" (the broad majority bucket the loam-family classes
    genuinely occupy) rather than risk a wrong extreme label. Returns ``None``
    (never invented) when any input is missing.
    """
    if clay_pct is None or sand_pct is None or silt_pct is None:
        return None
    if clay_pct >= 40:
        return SoilType.CLAY.value
    if silt_pct >= 80 and clay_pct < 12:
        return SoilType.SILT.value
    if sand_pct >= 70 and clay_pct < 15:
        return SoilType.SANDY.value
    return SoilType.LOAMY.value


def deficient_micronutrients(values: dict[str, float] | None) -> tuple[str, ...]:
    if not values:
        return ()
    out = [
        name
        for name, floor in MICRONUTRIENT_FLOORS.items()
        if name in values and values[name] is not None and values[name] < floor
    ]
    return tuple(out)


def assess(values: SoilValues) -> SoilAssessment:
    """Classify every parameter (pure)."""
    has_any = any(
        v is not None
        for v in (
            values.ph,
            values.organic_carbon,
            values.nitrogen,
            values.phosphorus,
            values.potassium,
            values.ec_salinity,
        )
    )
    return SoilAssessment(
        ph_class=classify_ph(values.ph),
        organic_carbon=classify_organic_carbon(values.organic_carbon),
        nitrogen=classify_nitrogen(values.nitrogen),
        phosphorus=classify_phosphorus(values.phosphorus),
        potassium=classify_potassium(values.potassium),
        salinity=classify_salinity(values.ec_salinity),
        deficient_micronutrients=deficient_micronutrients(values.micronutrients),
        has_any_value=has_any,
    )


# --------------------------------------------------------------------------- #
# Generic recommendations (no brands, never fabricated)
# --------------------------------------------------------------------------- #
def _rec(
    category: RecommendationCategory,
    key: str,
    severity: Severity,
    *,
    parameter: str | None = None,
    rating: str | None = None,
    value: float | None = None,
) -> RecommendationDraft:
    return RecommendationDraft(
        category=category.value,
        code=f"soil.rec.{category.value}.{key}",
        severity=severity.value,
        priority=_priority_for(severity.value),
        parameter=parameter,
        rating=rating,
        value=value,
        unit=PARAMETER_UNITS.get(parameter or "") or None,
    )


# Nutrient rating → (recommendation key, severity).
_NUTRIENT_RULE: dict[str, tuple[str, Severity]] = {
    _R.LOW.value: ("low", _S.WARNING),
    _R.MEDIUM.value: ("medium", _S.ADVICE),
    _R.HIGH.value: ("high", _S.INFO),
}


def build_recommendations(values: SoilValues) -> list[RecommendationDraft]:
    """Generic agronomic advice from the assessed values (pure, no brands)."""
    a = assess(values)
    recs: list[RecommendationDraft] = []

    def add(
        category: RecommendationCategory,
        key: str,
        severity: Severity,
        *,
        parameter: str | None = None,
        rating: str | None = None,
        value: float | None = None,
    ) -> None:
        recs.append(_rec(category, key, severity, parameter=parameter, rating=rating, value=value))

    # pH
    _ph_rule: dict[str, tuple[str, Severity]] = {
        PhClass.STRONGLY_ACIDIC.value: ("strongly_acidic", _S.CRITICAL),
        PhClass.ACIDIC.value: ("acidic", _S.WARNING),
        PhClass.NEUTRAL.value: ("neutral", _S.INFO),
        PhClass.ALKALINE.value: ("alkaline", _S.WARNING),
        PhClass.STRONGLY_ALKALINE.value: ("strongly_alkaline", _S.CRITICAL),
    }
    if a.ph_class in _ph_rule:
        key, sev = _ph_rule[a.ph_class]
        add(_C.PH, key, sev, parameter="ph", rating=a.ph_class, value=values.ph)

    # Organic carbon + N/P/K (same low/medium/high rule)
    for category, param, rating, value in (
        (_C.ORGANIC_CARBON, "organic_carbon", a.organic_carbon, values.organic_carbon),
        (_C.NITROGEN, "nitrogen", a.nitrogen, values.nitrogen),
        (_C.PHOSPHORUS, "phosphorus", a.phosphorus, values.phosphorus),
        (_C.POTASSIUM, "potassium", a.potassium, values.potassium),
    ):
        if rating in _NUTRIENT_RULE:
            key, sev = _NUTRIENT_RULE[rating]
            add(category, key, sev, parameter=param, rating=rating, value=value)

    # Micronutrients (one generic advice per deficient element)
    for element in a.deficient_micronutrients:
        add(_C.MICRONUTRIENT, "deficient", _S.WARNING, parameter=element, rating=_R.LOW.value)

    # Salinity
    if a.salinity == _R.HIGH.value:
        add(
            _C.GENERAL,
            "salinity_high",
            _S.CRITICAL,
            parameter="ec_salinity",
            rating=a.salinity,
            value=values.ec_salinity,
        )
    elif a.salinity == _R.MEDIUM.value:
        add(
            _C.GENERAL,
            "salinity_medium",
            _S.WARNING,
            parameter="ec_salinity",
            rating=a.salinity,
            value=values.ec_salinity,
        )

    # Drainage
    if values.drainage == DrainageClass.POOR.value:
        add(_C.DRAINAGE, "poor", _S.WARNING, parameter="drainage", rating=values.drainage)
    elif values.drainage == DrainageClass.EXCESSIVE.value:
        add(_C.DRAINAGE, "excessive", _S.ADVICE, parameter="drainage", rating=values.drainage)

    # Soil-type baseline guidance (farmer-entered soil_type; not fabricated)
    soil_type = (values.soil_type or "").strip().lower()
    if "sand" in soil_type:
        add(_C.WATER_HOLDING, "sandy", _S.ADVICE, parameter="soil_type", rating=soil_type)
    elif "clay" in soil_type:
        add(_C.DRAINAGE, "clay", _S.ADVICE, parameter="soil_type", rating=soil_type)

    # No measured values at all → advise getting a soil test.
    if not a.has_any_value and not a.deficient_micronutrients:
        add(_C.GENERAL, "no_data", _S.ADVICE)

    return recs


def worst_severity(recs: list[RecommendationDraft]) -> str | None:
    """The highest-severity recommendation present (for alerts). ``None`` if empty."""
    from app.modules.soil.constants import SEVERITY_ORDER

    if not recs:
        return None
    return max(recs, key=lambda r: SEVERITY_ORDER.get(r.severity, 0)).severity
