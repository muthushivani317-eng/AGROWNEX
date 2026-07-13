"""Decision Engine (docs: DECISION ENGINE).

Pure. Turns the module signals + health sub-scores into a ranked list of priority
issues and an overall risk level. Cross-module conditions escalate risk; missing data
is never invented — it simply produces fewer issues and a lower confidence upstream.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.modules.intelligence.constants import (
    RISK_BY_ORDER,
    RISK_HIGH_MIN,
    RISK_LOW_MIN,
    RISK_MEDIUM_MIN,
    RISK_ORDER,
    SEVERITY_ORDER,
    IssueSeverity,
    RiskLevel,
)
from app.modules.intelligence.engine import HealthScores
from app.modules.intelligence.signals import IntelligenceInputs

_S = IssueSeverity


@dataclass(frozen=True)
class PriorityIssue:
    code: str
    severity: str
    modules: tuple[str, ...]

    @property
    def rank(self) -> int:
        return SEVERITY_ORDER.get(self.severity, 0)


def _issue(code: str, severity: IssueSeverity, *modules: str) -> PriorityIssue:
    return PriorityIssue(
        code=f"intelligence.issue.{code}", severity=severity.value, modules=modules
    )


def detect_issues(
    inputs: IntelligenceInputs, scores: HealthScores
) -> list[PriorityIssue]:
    """The transparent priority-issue list, most severe first (pure)."""
    issues: list[PriorityIssue] = []

    d = inputs.disease
    if d is not None and scores.disease is not None and scores.disease < 70:
        sev = (
            _S.CRITICAL
            if d.severity == "high"
            else _S.WARNING
            if d.severity == "moderate"
            else _S.ADVICE
        )
        issues.append(_issue("disease_active", sev, "disease"))

    n = inputs.nutrient
    if n is not None and n.primary and n.status in ("confirmed", "possible"):
        sev = (
            _S.CRITICAL
            if n.status == "confirmed" and n.severity == "severe"
            else _S.WARNING
            if n.status == "confirmed"
            else _S.ADVICE
        )
        issues.append(_issue("nutrient_deficiency", sev, "nutrient", "soil"))

    s = inputs.soil
    if s is not None and s.has_data:
        lows = sum(1 for r in (s.nitrogen, s.phosphorus, s.potassium) if r == "low")
        if s.salinity == "high":
            issues.append(_issue("soil_salinity", _S.WARNING, "soil"))
        if lows or s.deficient_micronutrients:
            sev = _S.WARNING if lows >= 2 or s.deficient_micronutrients else _S.ADVICE
            code = "soil_low_nitrogen" if s.nitrogen == "low" else "soil_deficiency"
            issues.append(_issue(code, sev, "soil"))

    sat = inputs.satellite
    if sat is not None:
        declining = (
            sat.trend == "declining"
            or sat.vegetation_health in ("bare", "very_low", "low")
            or bool(sat.alert_codes)
        )
        if declining:
            sev = _S.CRITICAL if sat.stress_level == "severe" else _S.WARNING
            issues.append(_issue("vegetation_decline", sev, "satellite"))
        if sat.moisture_status in ("very_dry", "dry"):
            sev = _S.WARNING if sat.moisture_status == "very_dry" else _S.ADVICE
            issues.append(_issue("moisture_stress", sev, "satellite", "weather"))

    w = inputs.weather
    if w is not None:
        if any(c.startswith("heavy_rain") for c in w.insight_codes):
            issues.append(_issue("weather_heavy_rain", _S.WARNING, "weather"))
        if any(c.startswith("heat_stress") for c in w.insight_codes):
            issues.append(_issue("weather_heat", _S.WARNING, "weather"))

    g = inputs.growth
    if g is not None and (g.risk_level == "high" or (g.health_delta or 0) <= -5):
        issues.append(_issue("growth_decline", _S.WARNING, "growth"))

    if inputs.calendar.missed > 0:
        sev = _S.WARNING if inputs.calendar.missed >= 3 else _S.ADVICE
        issues.append(_issue("missed_tasks", sev, "calendar"))

    issues.sort(key=lambda i: i.rank, reverse=True)
    return issues


def _base_risk(overall: int | None) -> str:
    if overall is None or overall >= RISK_LOW_MIN:
        return RiskLevel.LOW.value
    if overall >= RISK_MEDIUM_MIN:
        return RiskLevel.MEDIUM.value
    if overall >= RISK_HIGH_MIN:
        return RiskLevel.HIGH.value
    return RiskLevel.CRITICAL.value


def _forces_critical(inputs: IntelligenceInputs) -> bool:
    d, n, s, sat = inputs.disease, inputs.nutrient, inputs.soil, inputs.satellite
    if d is not None and d.severity == "high" and (d.confidence or 0) >= 70:
        return True
    if n is not None and n.status == "confirmed" and n.severity == "severe":
        return True
    if s is not None and s.salinity == "high":
        return True
    if sat is not None and sat.stress_level == "severe":
        return True
    return False


def assess_risk(
    inputs: IntelligenceInputs, scores: HealthScores, issues: list[PriorityIssue]
) -> str:
    """Overall risk level from the health score + escalating cross-module conditions."""
    order = RISK_ORDER[_base_risk(scores.overall)]

    if _forces_critical(inputs):
        order = max(order, RISK_ORDER[RiskLevel.CRITICAL.value])
    elif any(i.severity == IssueSeverity.CRITICAL.value for i in issues):
        order = max(order, RISK_ORDER[RiskLevel.HIGH.value])

    # Near-term weather risk when combined with an active crop problem.
    adverse_weather = inputs.weather is not None and any(
        c.startswith(("heavy_rain", "heat_stress", "cold")) for c in inputs.weather.insight_codes
    )
    crop_problem = any(
        i.code.endswith(("disease_active", "vegetation_decline")) for i in issues
    )
    if adverse_weather and crop_problem:
        order = max(order, RISK_ORDER[RiskLevel.MEDIUM.value])

    return RISK_BY_ORDER[order]
