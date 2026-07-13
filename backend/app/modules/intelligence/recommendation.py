"""Recommendation Engine (docs: RECOMMENDATION ENGINE).

Pure. Prioritizes the top recommendations from all available evidence using
transparent cross-module rules — e.g. treat a high-confidence disease before a
nutrient deficiency; satellite vigor decline with healthy leaves → inspect
irrigation; heavy-rain forecast with disease risk → preventive advisory. Every
recommendation is a generic localization ``code`` (no commercial brands), and none
is invented when the evidence is absent.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.modules.intelligence.constants import (
    HEALTHY_MIN,
    LOW_CONFIDENCE,
    PRIORITY_ORDER,
    Priority,
    RiskLevel,
)
from app.modules.intelligence.decision import PriorityIssue
from app.modules.intelligence.engine import HealthScores
from app.modules.intelligence.signals import IntelligenceInputs

_P = Priority

MAX_RECOMMENDATIONS = 5


@dataclass(frozen=True)
class RecommendationDraft:
    code: str
    priority: str
    category: str
    modules: tuple[str, ...]


def _has_issue(issues: list[PriorityIssue], suffix: str) -> bool:
    return any(i.code.endswith(suffix) for i in issues)


def generate_recommendations(
    inputs: IntelligenceInputs,
    scores: HealthScores,
    issues: list[PriorityIssue],
    risk: str,
) -> list[RecommendationDraft]:
    """The prioritized top-5 recommendations (pure, generic codes only)."""
    drafts: list[RecommendationDraft] = []

    def add(key: str, priority: Priority, category: str, *modules: str) -> None:
        code = f"intelligence.rec.{key}"
        if any(d.code == code for d in drafts):
            return
        drafts.append(
            RecommendationDraft(
                code=code,
                priority=priority.value,
                category=category,
                modules=modules,
            )
        )

    d = inputs.disease
    disease_active = _has_issue(issues, "disease_active")
    disease_high_conf = d is not None and (d.confidence or 0) >= 60
    heavy_rain = inputs.weather is not None and any(
        c.startswith("heavy_rain") for c in inputs.weather.insight_codes
    )
    veg_decline = _has_issue(issues, "vegetation_decline")
    moisture_stress = _has_issue(issues, "moisture_stress")
    nitrogen_low = (
        inputs.soil is not None
        and inputs.soil.has_data
        and inputs.soil.nitrogen == "low"
    )
    nutrient_active = (
        inputs.nutrient is not None
        and inputs.nutrient.primary is not None
        and inputs.nutrient.status in ("confirmed", "possible")
    )

    # 1) Treat a confident disease first (docs: treat disease first if confidence high).
    if disease_active and disease_high_conf:
        add("treat_disease", _P.HIGH, "treatment", "disease")

    # 2) Low soil nitrogen + a nitrogen/nutrient signal → prioritize nitrogen.
    if nitrogen_low and (
        nutrient_active or (inputs.nutrient is not None and inputs.nutrient.primary == "nitrogen")
    ):
        add("address_nitrogen", _P.HIGH, "nutrition", "soil", "nutrient")
    elif nutrient_active:
        priority = _P.HIGH if inputs.nutrient.status == "confirmed" else _P.MEDIUM
        add("address_nutrient", priority, "nutrition", "nutrient")

    # 3) Satellite vigor decline with healthy leaves → inspect irrigation.
    if veg_decline and not disease_active and not nutrient_active:
        add("check_irrigation", _P.HIGH, "irrigation", "satellite")

    # 4) Heavy-rain forecast + disease risk → preventive advisory.
    if heavy_rain and (disease_active or (d is not None and (scores.disease or 100) < 80)):
        add("preventive_advisory", _P.HIGH, "preventive", "weather", "disease")

    # 5) Moisture stress and no rain coming → irrigate.
    if moisture_stress and not heavy_rain:
        add("irrigate", _P.MEDIUM, "irrigation", "satellite")

    # 6) Missed calendar tasks → catch up.
    if inputs.calendar.missed > 0:
        add("catch_up_tasks", _P.MEDIUM, "task", "calendar")

    # 7) Low confidence → gather more data to sharpen the assessment.
    if scores.confidence < LOW_CONFIDENCE:
        add("gather_more_data", _P.MEDIUM, "data")

    # 8) High/critical risk → expert (await one if already open).
    if risk in (RiskLevel.HIGH.value, RiskLevel.CRITICAL.value):
        if inputs.expert.open_consultation:
            add("await_expert", _P.LOW, "expert", "expert")
        else:
            add("consult_expert", _P.HIGH, "expert", "expert")

    # 9) Healthy and quiet → maintain the routine.
    if not issues and scores.overall is not None and scores.overall >= HEALTHY_MIN:
        add("maintain", _P.LOW, "maintain")

    drafts.sort(key=lambda d: PRIORITY_ORDER.get(d.priority, 3))
    return drafts[:MAX_RECOMMENDATIONS]
