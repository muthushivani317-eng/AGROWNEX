"""API contracts for experimental Groundnut inference."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class RankedPredictionOut(BaseModel):
    class_id: str
    display_name: str
    confidence: float = Field(ge=0, le=1)


class ImageQualityOut(BaseModel):
    status: Literal["accepted", "rejected"]
    reasons: list[str]
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    brightness: float
    contrast: float
    blur_score: float


class GroundnutPredictionResponse(BaseModel):
    request_id: UUID
    crop: Literal["groundnut"] = "groundnut"
    model_version: Literal["groundnut-efficientnet-b2-v1"] = "groundnut-efficientnet-b2-v1"
    experimental: Literal[True] = True
    experimental_notice: str
    status: Literal["accepted", "review_required", "rejected"]
    predicted_disease: RankedPredictionOut | None
    confidence_category: Literal["HIGH", "MEDIUM", "LOW"] | None
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    top_three_predictions: list[RankedPredictionOut] = Field(max_length=3)
    candidate_prediction: RankedPredictionOut | None
    image_quality: ImageQualityOut
    rejection_reasons: list[str]
    expert_review_required: bool
    runtime_device: str
    processing_time_ms: int = Field(ge=0)


GroundnutTextSymptom = Literal[
    "dark_leaf_spots",
    "light_leaf_spots",
    "yellow_halo_around_spots",
    "rust_colored_leaf_marks",
    "general_leaf_yellowing",
    "yellowing_between_leaf_veins",
    "leaf_curling",
    "wilting",
    "stunted_growth",
    "holes_or_chewed_edges",
    "uniform_green_leaves",
]


class GroundnutTextSymptomRequest(BaseModel):
    symptoms: list[GroundnutTextSymptom] = Field(min_length=1, max_length=8)


class GroundnutTextGuidanceResponse(BaseModel):
    crop: Literal["groundnut"] = "groundnut"
    status: Literal["preliminary_guidance"] = "preliminary_guidance"
    observed_symptoms: list[GroundnutTextSymptom]
    possible_patterns: list[
        Literal[
            "leaf_spot_pattern",
            "rust_like_pattern",
            "nutrient_or_stress_pattern",
            "general_stress_pattern",
            "possible_pest_damage_pattern",
            "no_obvious_symptom_pattern",
        ]
    ]
    guidance: str
    expert_review_required: Literal[True] = True
    confirmed_disease: None = None
    image_model_confidence: None = None
    warnings: list[str]


class GroundnutTranscriptResponse(BaseModel):
    transcript: str = Field(min_length=1, max_length=4000)


class GroundnutTranscriptMapRequest(BaseModel):
    transcript: str = Field(min_length=1, max_length=4000)
    language: Literal["en-IN", "ta-IN", "ml-IN"]


class GroundnutTranscriptMapResponse(BaseModel):
    matched_symptoms: list[GroundnutTextSymptom]
    unmatched_text: list[str]
    ambiguous_text: list[str]


class GroundnutPestObservationResponse(BaseModel):
    observation_id: UUID
    crop: Literal["groundnut"] = "groundnut"
    status: Literal["pending_expert_review"] = "pending_expert_review"
    damage_extent: Literal["few", "several", "widespread"]
    spread_speed: Literal["unknown", "stable", "rapid"]
    consent: Literal[True] = True
    private_photo_stored: Literal[True] = True
    pest_label: None = None
    diagnosis: None = None
