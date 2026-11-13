"""Crop Intelligence request/response schemas (docs: reuse response envelope).

Scores, risk, issues and recommendations travel as numbers / localization ``code``s
so the Tamil-first client renders them. A module with no data is ``null`` — never
fabricated.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.intelligence.constants import MIN_OVERALL_EVIDENCE_MODULES
from app.modules.intelligence.models import (
    CropDecisionHistory,
    CropIntelligenceReport,
)
from app.modules.nutrient.crops import is_groundnut_nutrient_crop


class HealthScoresOut(BaseModel):
    overall_health_score: int | None
    confidence: int
    disease_score: int | None
    nutrient_score: int | None
    soil_score: int | None
    satellite_score: int | None
    weather_score: int | None
    growth_score: int | None


class PriorityIssueOut(BaseModel):
    code: str
    severity: str
    modules: list[str]


class RecommendationOut(BaseModel):
    code: str
    priority: str
    category: str
    modules: list[str]


class IntelligenceReportOut(BaseModel):
    id: uuid.UUID
    farm_id: uuid.UUID
    crop: str | None
    generated_at: datetime
    overall_health_score: int | None
    confidence: int | None
    overall_risk: str
    risk_score: int | None
    sources_used: list[str]
    health: HealthScoresOut | None
    priority_issues: list[PriorityIssueOut]
    recommendations: list[RecommendationOut]
    created_at: datetime

    @classmethod
    def from_report(cls, report: CropIntelligenceReport) -> IntelligenceReportOut:
        # Reports created before evidence gating may contain an aggregate derived from
        # only one module. Preserve the module finding, but fail closed at the API.
        restricted = is_groundnut_nutrient_crop(report.crop)
        safe_sources = set(report.sources_used or [])
        if restricted:
            safe_sources.discard("nutrient")

        sufficient = "nutrient" not in (report.sources_used or []) and len(safe_sources) >= MIN_OVERALL_EVIDENCE_MODULES
        safe_overall = report.overall_health_score if sufficient else None
        health = None
        if report.health is not None:
            h = report.health
            health = HealthScoresOut(
                overall_health_score=h.overall_health_score if sufficient else None,
                confidence=h.confidence,
                disease_score=h.disease_score,
                nutrient_score=h.nutrient_score,
                soil_score=h.soil_score,
                satellite_score=h.satellite_score,
                weather_score=h.weather_score,
                growth_score=h.growth_score,
            )
        restricted = is_groundnut_nutrient_crop(report.crop)
        issues = [
            PriorityIssueOut(
                code=i.get("code", ""),
                severity=i.get("severity", "info"),
                modules=list(i.get("modules", [])),
            )
            for i in ((report.risk.priority_issues or []) if report.risk else [])
            if not (restricted and "nutrient" in i.get("modules", []))
        ]
        recs = [
            r
            for r in sorted(report.recommendations, key=lambda r: r.rank)
            if not (restricted and "nutrient" in (r.modules or []))
        ]
        if restricted and health is not None:
            health.nutrient_score = None
        return cls(
            id=report.id,
            farm_id=report.farm_id,
            crop=report.crop,
            generated_at=report.generated_at,
            overall_health_score=safe_overall,
            confidence=report.confidence if sufficient else None,
            overall_risk=report.overall_risk if sufficient else "unknown",
            risk_score=(report.risk.risk_score if report.risk else None) if sufficient else None,
            sources_used=list(report.sources_used or []),
            health=health,
            priority_issues=issues,
            recommendations=[
                RecommendationOut(
                    code=r.code,
                    priority=r.priority,
                    category=r.category,
                    modules=list(r.modules or []),
                )
                for r in recs
            ],
            created_at=report.created_at,
        )


class IntelligenceDashboardOut(BaseModel):
    farm_id: uuid.UUID
    has_data: bool
    message_code: str | None
    report: IntelligenceReportOut | None


class IntelligenceHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    farm_id: uuid.UUID
    report_id: uuid.UUID | None
    overall_health_score: int | None
    overall_risk: str
    confidence: int | None
    recorded_at: datetime

    @classmethod
    def from_history(cls, h: CropDecisionHistory) -> IntelligenceHistoryOut:
        return cls(
            id=h.id,
            farm_id=h.farm_id,
            report_id=h.report_id,
            overall_health_score=(
                h.overall_health_score
                if getattr(h, "_sufficient_evidence", False)
                else None
            ),

            overall_risk=h.overall_risk if getattr(h, "_sufficient_evidence", False) else "unknown",
            confidence=h.confidence if getattr(h, "_sufficient_evidence", False) else None,
            recorded_at=h.recorded_at,
        )