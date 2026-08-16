from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SupportedCropId = Literal["banana", "paddy", "cotton", "groundnut", "redgram", "chilli"]
CropIdentificationStatus = Literal[
    "identified",
    "uncertain",
    "unsupported",
    "non_plant",
    "invalid_image",
    "service_unavailable",
]


class LocalizedText(BaseModel):
    model_config = ConfigDict(extra="forbid")
    en: str = Field(min_length=1, max_length=300)
    ta: str = Field(min_length=1, max_length=300)


class QualityChecks(BaseModel):
    model_config = ConfigDict(extra="forbid")
    passed: bool
    reason_code: str | None = None
    width: int = Field(ge=0)
    height: int = Field(ge=0)
    byte_size: int = Field(ge=0)


class PlantCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    outcome: Literal["plant", "non_plant", "uncertain"]
    method: Literal["temporary_gemini_provider_assisted"]


class GeminiCropIdentification(BaseModel):
    """Strict, untrusted provider response. Never returned directly to clients."""

    model_config = ConfigDict(extra="forbid")
    status: Literal["identified", "uncertain", "unsupported", "non_plant"]
    crop_id: SupportedCropId | None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence_available: bool
    reason_code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{2,63}$")
    plant_outcome: Literal["plant", "non_plant", "uncertain"]
    needs_another_image: bool

    @model_validator(mode="after")
    def consistent(self) -> GeminiCropIdentification:
        if self.confidence_available != (self.confidence is not None):
            raise ValueError("confidence availability mismatch")
        if self.status == "identified" and (self.crop_id is None or self.plant_outcome != "plant"):
            raise ValueError("identified result requires a supported plant crop")
        if self.status != "identified" and self.crop_id is not None:
            raise ValueError("non-identified result cannot contain a crop")
        return self


class CropIdentificationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(min_length=16, max_length=64)
    status: CropIdentificationStatus
    identified_crop: SupportedCropId | None
    display_name: LocalizedText
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence_source: Literal["gemini_self_report", "heuristic", "unavailable"]
    farmer_confirmation_required: Literal[True] = True
    reason_code: str
    reason_message: LocalizedText
    provider: Literal["gemini"] = "gemini"
    provider_model: str = Field(min_length=1, max_length=120)
    crop_id_version: str = Field(min_length=1, max_length=40)
    quality_checks: QualityChecks
    plant_check: PlantCheck
    created_at: datetime


class CropConfirmationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(min_length=16, max_length=64)
    confirmed_crop: SupportedCropId
    decision: Literal["confirmed", "farmer_selected_after_rejection"]


class CropConfirmationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str
    confirmed_crop: SupportedCropId
    crop_source: Literal["gemini_confirmed", "farmer_selected_after_rejection"]
    confirmation_token: str = Field(min_length=32, max_length=128)
    confirmed_at: datetime
    expires_at: datetime
