"""Pydantic v2 API contracts for Banana V3."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ResultStatus(StrEnum):
    accepted = "accepted"
    uncertain = "uncertain"
    error = "error"


class ResultBlock(BaseModel):
    class_id: str | None = None
    display_name_key: str | None = None
    confidence: float = Field(ge=0, le=1)
    margin: float = Field(ge=0, le=1)


class GateBlock(BaseModel):
    predicted_class: str | None = None
    confidence: float = Field(ge=0, le=1)
    margin: float = Field(ge=0, le=1)
    accepted: bool


class DiseaseBlock(GateBlock):
    executed: bool


class PredictionResponse(BaseModel):
    request_id: UUID
    model_version: Literal["banana-v3.0.0"] = "banana-v3.0.0"
    crop: Literal["banana"] = "banana"
    status: ResultStatus
    decision_code: str
    result: ResultBlock
    healthy_gate: GateBlock
    disease_classifier: DiseaseBlock
    message_key: str
    requires_follow_up_photo: bool
    requires_human_review: bool
    runtime_backend: Literal["onnx", "pytorch"]
    processing_time_ms: int = Field(ge=0)
    timestamp_utc: datetime


class FeedbackChoice(StrEnum):
    CORRECT = "CORRECT"
    INCORRECT = "INCORRECT"
    UNSURE = "UNSURE"
    IMAGE_POOR = "IMAGE_POOR"
    NOT_BANANA = "NOT_BANANA"
    OTHER = "OTHER"


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    request_id: UUID = Field(default_factory=uuid4)
    prediction_request_id: UUID
    farmer_selected_outcome: FeedbackChoice
    reviewer_selected_outcome: FeedbackChoice | None = None
    corrected_class: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)
    consent: bool
    source_context: Literal[
        "KVK_SUPERVISED_TEST",
        "FARMER_APP",
        "INTERNAL_REVIEW",
        "OTHER",
        "agrowai_mobile_app",
    ]
    consented_image_storage_reference: str | None = Field(default=None, max_length=500)


class BatchPredictionResponse(BaseModel):
    results: list[PredictionResponse]
