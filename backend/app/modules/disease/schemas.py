"""Disease request/response schemas (docs/API_CONTRACT.md → DISEASE)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.core.config import settings
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


GroundnutPestReviewFeedback = Literal[
    "monitor_field_conditions",
    "submit_clearer_photo",
    "seek_in_person_field_assessment",
    "no_actionable_conclusion_from_photo",
]


class FarmerGroundnutPestObservationOut(BaseModel):
    damage_extent: Literal["few", "several", "widespread"]
    spread_speed: Literal["unknown", "stable", "rapid"]
    review_status: Literal["pending", "reviewed"]
    feedback: GroundnutPestReviewFeedback | None = None
    review_timestamp: datetime | None = None


def _farmer_pest_observation(
    report: DiseaseReport,
) -> FarmerGroundnutPestObservationOut | None:
    if report.crop != "groundnut" or report.review_consent is not True:
        return None
    raw = report.raw_response if isinstance(report.raw_response, dict) else {}
    if raw.get("record_type") != "farmer_pest_damage_observation":
        return None
    reported = raw.get("farmer_reported")
    if not isinstance(reported, dict) or report.review_status not in {"pending", "reviewed"}:
        return None
    extent = reported.get("damage_extent")
    spread = reported.get("spread_speed")
    if extent not in {"few", "several", "widespread"} or spread not in {
        "unknown",
        "stable",
        "rapid",
    }:
        return None
    review = raw.get("review") if isinstance(raw.get("review"), dict) else {}
    feedback = review.get("feedback")
    if feedback not in {
        None,
        "monitor_field_conditions",
        "submit_clearer_photo",
        "seek_in_person_field_assessment",
        "no_actionable_conclusion_from_photo",
    }:
        feedback = None
    return FarmerGroundnutPestObservationOut(
        damage_extent=extent,
        spread_speed=spread,
        review_status=report.review_status,
        feedback=feedback,
        review_timestamp=report.review_timestamp,
    )


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
    conventional_category_english: str | None
    conventional_category_tamil: str | None
    visible_parts: list[str]
    needs_expert_review: bool
    explanation_tamil: str | None
    explanation_english: str | None
    image_url: str | None
    private_image_available: bool
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
    pest_observation: FarmerGroundnutPestObservationOut | None = None

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
            conventional_category_english=report.conventional_category_english,
            conventional_category_tamil=report.conventional_category_tamil,
            visible_parts=report.visible_parts or [],
            needs_expert_review=report.needs_expert_review,
            explanation_tamil=report.explanation_tamil,
            explanation_english=report.explanation_english,
            image_url=(
                None
                if settings.private_disease_images_enabled and report.image_key
                else report.image_url
            ),
            private_image_available=bool(report.image_key),
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
            pest_observation=_farmer_pest_observation(report),
        )


class DiseaseReportSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    crop: str | None
    disease: str | None
    confidence: int | None
    severity: str | None
    image_url: str | None
    private_image_available: bool = False
    needs_expert_review: bool
    test_mode: dict | None
    verification_level: str | None
    created_at: datetime
    pest_observation: FarmerGroundnutPestObservationOut | None = None

    @classmethod
    def from_report(cls, report: DiseaseReport) -> DiseaseReportSummaryOut:
        updates = {
            "private_image_available": bool(report.image_key),
            "pest_observation": _farmer_pest_observation(report),
        }
        if settings.private_disease_images_enabled and report.image_key:
            updates["image_url"] = None
        return cls.model_validate(report).model_copy(update=updates)


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


class GroundnutPestObservationReviewOut(BaseModel):
    """Privacy-minimized KVK view; farmer and farm identifiers are excluded."""

    observation_id: uuid.UUID
    damage_extent: Literal["few", "several", "widespread"]
    spread_speed: Literal["unknown", "stable", "rapid"]
    review_status: Literal["pending"] = "pending"
    private_photo_available: bool
    submitted_at: datetime


class GroundnutPestObservationCompletionRequest(BaseModel):
    feedback: GroundnutPestReviewFeedback


class GroundnutPestObservationCompletionOut(BaseModel):
    observation_id: uuid.UUID
    review_status: Literal["reviewed"] = "reviewed"
    feedback: GroundnutPestReviewFeedback
    reviewer_role: Literal["kvk_officer"] = "kvk_officer"
    review_timestamp: datetime
