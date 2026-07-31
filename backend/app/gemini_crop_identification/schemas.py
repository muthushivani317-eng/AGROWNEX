from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SupportedCropId = Literal[
    "banana", "paddy", "cotton", "groundnut", "redgram", "chilli"
]
CropId = Literal[
    "banana", "paddy", "cotton", "groundnut", "redgram", "chilli", "unknown", "non_plant"
]


class GeminiCropIdentification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["identified", "uncertain", "non_plant", "invalid_image"]
    crop_id: CropId
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1, max_length=240)
    visible_evidence: list[str] = Field(max_length=8)
    needs_another_image: bool


class CropIdentificationResponse(GeminiCropIdentification):
    requires_user_confirmation: Literal[True] = True
    can_continue_to_disease_detection: Literal[False] = False
    provider: Literal["gemini"] = "gemini"
    field_validated: Literal[False] = False

