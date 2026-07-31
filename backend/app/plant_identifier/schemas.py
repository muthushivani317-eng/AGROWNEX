from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PlantStatus = Literal[
    "identified", "uncertain", "non_plant", "invalid_image", "provider_error"
]


class PlantAlternative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    common_name: str = Field(min_length=1, max_length=120)
    scientific_name: str | None = Field(default=None, max_length=160)
    confidence: float = Field(ge=0.0, le=1.0)


class GeminiPlantIdentification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["identified", "uncertain", "non_plant"]
    common_name: str | None = Field(default=None, max_length=120)
    scientific_name: str | None = Field(default=None, max_length=160)
    family: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=800)
    visible_characteristics: list[str] = Field(default_factory=list, max_length=10)
    possible_alternatives: list[PlantAlternative] = Field(
        default_factory=list, max_length=5
    )
    confidence: float = Field(ge=0.0, le=1.0)
    informational_only: Literal[True]
    used_for_disease_routing: Literal[False]

    @model_validator(mode="after")
    def enforce_status_contract(self) -> GeminiPlantIdentification:
        if self.status == "identified" and not self.common_name:
            raise ValueError("identified response requires common_name")
        if self.status == "non_plant":
            if any((self.common_name, self.scientific_name, self.family)):
                raise ValueError("non_plant response cannot claim plant identity")
            if self.possible_alternatives:
                raise ValueError("non_plant response cannot include plant alternatives")
        return self


class PlantIdentificationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1, max_length=128)
    status: PlantStatus
    common_name: str | None = None
    scientific_name: str | None = None
    family: str | None = None
    description: str | None = None
    visible_characteristics: list[str] = Field(default_factory=list)
    possible_alternatives: list[PlantAlternative] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    informational_only: Literal[True] = True
    used_for_disease_routing: Literal[False] = False
    disease_inference_available: Literal[False] = False
    crop_confirmation_created: Literal[False] = False
    provider: Literal["gemini"] = "gemini"
    language: Literal["ta", "en"] = "en"
    disclaimer: str
    processing_status: Literal["complete", "rejected", "failed"]
    error_code: str | None = None
    retry_allowed: bool = False

