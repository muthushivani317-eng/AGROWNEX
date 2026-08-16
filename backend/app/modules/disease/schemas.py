"""Disease request/response schemas (docs/API_CONTRACT.md → DISEASE)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.modules.disease.models import DiseaseReport


class ModelMetadataOut(BaseModel):
    model_family: str
    model_version: str
    supported_crops: list[str]
    supported_classes: list[str]
    threshold: float
    temperature: float
    runtime_status: str
    artifact_verification_status: str
    official_accuracy_claim: bool


class CropCapabilityOut(BaseModel):
    crop: str
    visible_in_app: bool
    dataset_verification_status: str
    disease_model_status: str
    disease_model_available: bool
    nutrient_model_available: bool
    satellite_support_available: bool
    production_approved: bool


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
    image_url: str | None
    thumbnail_url: str | None
    model_used: str | None
    review_status: str | None
    reviewer_role: str | None
    corrected_label: str | None
    review_timestamp: datetime | None
    review_consent: bool | None
    kvk_session: bool
    test_mode: dict | None
    verification_level: str | None
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
            review_status=report.review_status,
            reviewer_role=report.reviewer_role,
            corrected_label=report.corrected_label,
            review_timestamp=report.review_timestamp,
            review_consent=report.review_consent,
            kvk_session=report.kvk_session,
            test_mode=report.test_mode,
            verification_level=report.verification_level,
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
    image_url: str | None
    needs_expert_review: bool
    test_mode: dict | None
    verification_level: str | None
    created_at: datetime


class DiseaseReviewRequest(BaseModel):
    correct: bool
    corrected_label: Literal[
        "redgram__healthy", "redgram__leaf_spot", "redgram__sterility_mosaic"
    ] | None = None


class DiseaseReviewOut(BaseModel):
    report_id: uuid.UUID
    review_status: Literal["confirmed", "corrected"]
    corrected_label: str | None
    reviewer_role: Literal["kvk_officer"]
    review_timestamp: datetime
