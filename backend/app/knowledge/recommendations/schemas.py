from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

VERIFY_LABEL = "VERIFY AGAINST OFFICIAL SOURCE"


class MappingStatus(StrEnum):
    EXACT_SOURCE_MATCH = "EXACT_SOURCE_MATCH"
    REVIEWED_SYNONYM_MATCH = "REVIEWED_SYNONYM_MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    AMBIGUOUS_MATCH = "AMBIGUOUS_MATCH"
    NO_SOURCE_MATCH = "NO_SOURCE_MATCH"
    MODEL_LABEL_CONFLICT = "MODEL_LABEL_CONFLICT"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    MODEL_LABEL_PENDING_FINAL_RUNTIME = "MODEL_LABEL_PENDING_FINAL_RUNTIME"


class ReviewState(StrEnum):
    SOURCE_EXTRACTED = "SOURCE_EXTRACTED"
    SOURCE_MAPPED = "SOURCE_MAPPED"
    INTERNAL_REVIEW_REQUIRED = "INTERNAL_REVIEW_REQUIRED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    SOURCE_INCOMPLETE = "SOURCE_INCOMPLETE"
    TAMIL_TRANSLATION_REVIEW_REQUIRED = "TAMIL_TRANSLATION_REVIEW_REQUIRED"
    READY_FOR_INTERNAL_TESTING = "READY_FOR_INTERNAL_TESTING"
    BLOCKED_NO_SOURCE = "BLOCKED_NO_SOURCE"
    BLOCKED_MODEL_LABEL_CONFLICT = "BLOCKED_MODEL_LABEL_CONFLICT"
    BLOCKED_UNREADABLE_SOURCE = "BLOCKED_UNREADABLE_SOURCE"
    BLOCKED_REGULATORY_UNVERIFIED = "BLOCKED_REGULATORY_UNVERIFIED"


class LocalizedText(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ta: str | None = None
    en: str
    tamil_review_required: bool = True


class SourceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str
    source_title: str
    publisher: str | None = None
    source_pdf_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    printed_page: str | None = None
    pdf_page_index: int = Field(ge=0)
    section: str
    recommendation_item_id: str


class RecommendationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recommendation_id: str
    category: Literal[
        "symptom", "immediate_action", "prevention", "cultural_practice",
        "biological_option", "chemical_option", "monitoring", "escalation",
    ]
    text: LocalizedText
    raw_source_text: str
    crop_id: str
    disease_id: str
    source: SourceReference
    evidence_status: str
    review_status: ReviewState
    applicability_constraints: list[str] = []
    timing: str | None = None
    dose: str | None = None
    units: str | None = None
    warnings: list[str] = []
    contradiction_status: str = "NONE"
    active: bool = False
    active_ingredient: str | None = None
    brand_present_in_source: bool = False

    @model_validator(mode="after")
    def validate_activation(self) -> RecommendationItem:
        if self.active and self.review_status != ReviewState.READY_FOR_INTERNAL_TESTING:
            raise ValueError("active recommendation is not READY_FOR_INTERNAL_TESTING")
        if self.active and self.contradiction_status != "NONE":
            raise ValueError("active recommendation has unresolved conflict")
        if self.active and self.brand_present_in_source:
            raise ValueError("brand-containing recommendation cannot be active")
        if self.category == "chemical_option":
            if not self.active_ingredient:
                raise ValueError("chemical option requires an active ingredient")
            if self.source.pdf_page_index < 0:
                raise ValueError("chemical option requires a page citation")
        if self.dose is not None and not self.units:
            raise ValueError("dose requires explicit source units")
        return self


class RecommendationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    crop_id: Literal["banana", "rice", "cotton", "groundnut", "redgram", "chilli"]
    disease_id: str
    model_label: str
    display_name: LocalizedText
    mapping_status: MappingStatus
    recommendation_version: str
    source_set_version: str
    items: list[RecommendationItem] = []
    verification_label: Literal["VERIFY AGAINST OFFICIAL SOURCE"] = VERIFY_LABEL
    official_diagnosis: Literal[False] = False
    field_validated: Literal[False] = False
    expert_verified: Literal[False] = False
    recommendation_status: ReviewState
    last_reviewed_at: datetime | None = None
    active: bool = False

    @model_validator(mode="after")
    def validate_record_activation(self) -> RecommendationRecord:
        permitted = {
            MappingStatus.EXACT_SOURCE_MATCH,
            MappingStatus.REVIEWED_SYNONYM_MATCH,
        }
        if self.active and self.mapping_status not in permitted:
            raise ValueError("mapping status cannot activate recommendations")
        if self.active and self.recommendation_status != ReviewState.READY_FOR_INTERNAL_TESTING:
            raise ValueError("record is not ready for internal testing")
        if self.active and (not self.items or not all(item.active for item in self.items)):
            raise ValueError("active record requires active sourced items")
        return self


class RecommendationContext(BaseModel):
    crop_id: str
    model_label: str | None
    confidence_passed: bool
    crop_identity_matched: bool
    crop_identity_abstained: bool
    disease_abstained: bool
    healthy_result: bool
    runtime_integrity_passed: bool


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    available: bool
    reason_code: str
    crop_id: str
    model_label: str | None
    record: RecommendationRecord | None = None
    verification_warning: Literal["VERIFY AGAINST OFFICIAL SOURCE"] = VERIFY_LABEL
    official_diagnosis: Literal[False] = False
    field_validated: Literal[False] = False
    generated_at: datetime
