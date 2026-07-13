"""Nutrient request/response schemas (docs: reuse response envelope).

Deficiencies, symptoms and recommendations travel as localization ``code``s /
enum values so the Tamil-first client renders them. An unconfirmed or unavailable
value is ``null`` / ``not_confirmed`` and surfaced honestly — never fabricated.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.nutrient.models import (
    NutrientHistory,
    NutrientRecommendation,
    NutrientReport,
)

_MIME_PATTERN = "^image/(jpeg|png|webp)$"


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #
class AnalyzeNutrientRequest(BaseModel):
    image_base64: str = Field(min_length=16, max_length=24_000_000)
    mime_type: str = Field(pattern=_MIME_PATTERN)
    farm_id: uuid.UUID
    crop: str | None = Field(default=None, max_length=80)
    language: str | None = Field(default=None, pattern="^(ta|en)$")
    capture_method: str | None = Field(default=None, pattern="^(camera|gallery)$")
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


# --------------------------------------------------------------------------- #
# Outputs
# --------------------------------------------------------------------------- #
class NutrientRecommendationOut(BaseModel):
    category: str
    code: str
    nutrient: str | None
    severity: str
    priority: str

    @classmethod
    def from_model(cls, rec: NutrientRecommendation) -> NutrientRecommendationOut:
        return cls(
            category=rec.category,
            code=rec.code,
            nutrient=rec.nutrient,
            severity=rec.severity,
            priority=rec.priority,
        )


class NutrientAnalysisOut(BaseModel):
    primary_deficiency: str | None
    secondary_deficiency: str | None
    status: str
    confidence: int
    severity: str
    affected_area: str | None
    disease_conflict: bool
    needs_test: bool
    needs_expert: bool
    soil_reference: dict | None
    satellite_reference: dict | None
    weather_reference: dict | None
    explanation_tamil: str | None
    explanation_english: str | None


class NutrientReportOut(BaseModel):
    id: uuid.UUID
    farm_id: uuid.UUID
    crop: str | None
    image_url: str
    thumbnail_url: str | None
    capture_date: date | None
    provider: str
    model_used: str | None
    status: str
    language: str
    latitude: float | None
    longitude: float | None
    weather_snapshot: dict | None
    analysis: NutrientAnalysisOut | None
    symptoms: list[str]
    recommendations: list[NutrientRecommendationOut]
    created_at: datetime

    @classmethod
    def from_report(cls, report: NutrientReport) -> NutrientReportOut:
        analysis = None
        if report.analysis is not None:
            a = report.analysis
            analysis = NutrientAnalysisOut(
                primary_deficiency=a.primary_deficiency,
                secondary_deficiency=a.secondary_deficiency,
                status=a.status,
                confidence=a.confidence,
                severity=a.severity,
                affected_area=a.affected_area,
                disease_conflict=a.disease_conflict,
                needs_test=a.needs_test,
                needs_expert=a.needs_expert,
                soil_reference=a.soil_reference,
                satellite_reference=a.satellite_reference,
                weather_reference=a.weather_reference,
                explanation_tamil=a.explanation_tamil,
                explanation_english=a.explanation_english,
            )
        return cls(
            id=report.id,
            farm_id=report.farm_id,
            crop=report.crop,
            image_url=report.image_url,
            thumbnail_url=report.thumbnail_url,
            capture_date=report.capture_date,
            provider=report.provider,
            model_used=report.model_used,
            status=report.status,
            language=report.language,
            latitude=report.latitude,
            longitude=report.longitude,
            weather_snapshot=report.weather_snapshot,
            analysis=analysis,
            symptoms=[s.code for s in report.symptoms],
            recommendations=[
                NutrientRecommendationOut.from_model(r) for r in report.recommendations
            ],
            created_at=report.created_at,
        )


class NutrientReportSummaryOut(BaseModel):
    """A compact history row — status + primary deficiency + confidence."""

    id: uuid.UUID
    farm_id: uuid.UUID
    crop: str | None
    primary_deficiency: str | None
    status: str
    confidence: int
    severity: str | None
    recorded_at: datetime

    @classmethod
    def from_history(cls, h: NutrientHistory) -> NutrientReportSummaryOut:
        return cls(
            id=h.report_id or h.id,
            farm_id=h.farm_id,
            crop=h.crop,
            primary_deficiency=h.primary_deficiency,
            status=h.status,
            confidence=h.confidence,
            severity=h.severity,
            recorded_at=h.recorded_at,
        )


class NutrientHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    farm_id: uuid.UUID
    report_id: uuid.UUID | None
    crop: str | None
    primary_deficiency: str | None
    status: str
    confidence: int
    severity: str | None
    recorded_at: datetime
