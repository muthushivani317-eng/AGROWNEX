from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DifferentialDiagnosis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    disease: str = Field(min_length=1, max_length=120)
    likelihood: Literal["low", "medium", "high"]


class OpenAISecondOpinion(BaseModel):
    """Strict non-treatment output accepted from the comparison provider."""

    model_config = ConfigDict(extra="forbid")

    crop_assessment: Literal["consistent", "inconsistent", "uncertain"]
    assessment_status: Literal["possible", "uncertain", "not_assessable"]
    image_usable: bool
    outcome_category: Literal[
        "healthy",
        "known_disease",
        "abiotic_stress",
        "nutrient_related",
        "pest_damage",
        "physical_injury",
        "unsupported_disease",
        "insufficient_evidence",
    ]
    known_class_match: Literal["high", "medium", "low", "unknown"]
    possible_disease_label: str | None = Field(default=None, max_length=120)
    differential_diagnoses: list[DifferentialDiagnosis] = Field(
        default_factory=list, max_length=3
    )
    observed_symptoms: list[str] = Field(default_factory=list, max_length=8)
    evidence_supporting: list[str] = Field(default_factory=list, max_length=6)
    evidence_missing: list[str] = Field(default_factory=list, max_length=6)
    additional_photo_required: bool
    requested_photo_view: Literal[
        "whole_plant", "affected_leaf", "lesion_closeup", "leaf_underside"
    ] | None
    expert_review_required: bool


class DiagnosticDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal[
        "strong_agreement",
        "conflict_needs_more_evidence",
        "unsupported_or_unknown_disease",
        "insufficient_evidence",
        "expert_review_required",
    ]
    likely_disease_label: str | None = None
    additional_photo_required: bool = False
    requested_photo_view: Literal[
        "whole_plant", "affected_leaf", "lesion_closeup", "leaf_underside"
    ] | None = None
    expert_review_required: bool = False
    reason_code: str


class ComparisonOut(BaseModel):
    id: str
    subject_hash: str
    crop: str
    local_model: str
    local_status: str
    local_label: str | None
    local_confidence: float | None
    provider_status: str
    provider_model: str
    provider_label: str | None
    crop_assessment: str | None
    agrees_with_local: bool | None
    visual_observations: list[str]
    test_mode: Literal[True] = True
    exposed_to_farmer: Literal[False] = False
    created_at: str
