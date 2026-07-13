"""Disease request/response schemas (docs/API_CONTRACT.md → DISEASE)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.disease.models import DiseaseReport

_MIME_PATTERN = "^image/(jpeg|png|webp)$"


class AnalyzeRequest(BaseModel):
    image_base64: str = Field(min_length=16, max_length=24_000_000)
    mime_type: str = Field(pattern=_MIME_PATTERN)
    farm_id: uuid.UUID | None = None
    crop: str | None = Field(default=None, max_length=80)
    language: str | None = Field(default=None, pattern="^(ta|en)$")
    capture_method: str | None = Field(default=None, pattern="^(camera|gallery)$")
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class DiseaseReportOut(BaseModel):
    id: uuid.UUID
    farm_id: uuid.UUID | None
    crop: str | None
    crop_confidence: int | None
    disease: str | None
    confidence: int | None
    severity: str | None
    symptoms: list[str]
    causes: list[str]
    recommendations: list[str]
    prevention: list[str]
    visible_parts: list[str]
    needs_expert_review: bool
    explanation_tamil: str | None
    explanation_english: str | None
    image_url: str
    thumbnail_url: str | None
    model_used: str | None
    weather_snapshot: dict | None
    latitude: float | None
    longitude: float | None
    language: str
    created_at: datetime

    @classmethod
    def from_report(cls, report: DiseaseReport) -> DiseaseReportOut:
        return cls(
            id=report.id,
            farm_id=report.farm_id,
            crop=report.crop,
            crop_confidence=report.crop_confidence,
            disease=report.disease,
            confidence=report.confidence,
            severity=report.severity,
            symptoms=report.symptoms or [],
            causes=report.causes or [],
            recommendations=report.recommendations or [],
            prevention=report.prevention or [],
            visible_parts=report.visible_parts or [],
            needs_expert_review=report.needs_expert_review,
            explanation_tamil=report.explanation_tamil,
            explanation_english=report.explanation_english,
            image_url=report.image_url,
            thumbnail_url=report.thumbnail_url,
            model_used=report.model_used,
            weather_snapshot=report.weather_snapshot,
            latitude=report.latitude,
            longitude=report.longitude,
            language=report.language,
            created_at=report.created_at,
        )


class DiseaseReportSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    crop: str | None
    disease: str | None
    confidence: int | None
    severity: str | None
    image_url: str
    needs_expert_review: bool
    created_at: datetime
