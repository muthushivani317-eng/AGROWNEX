from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelAvailabilityStatus(StrEnum):
    FROZEN_RUNTIME_READY = "FROZEN_RUNTIME_READY"
    MODEL_PIPELINE_PENDING = "MODEL_PIPELINE_PENDING"
    MODEL_NOT_COMPLETED = "MODEL_NOT_COMPLETED"
    DATASET_UNRESOLVED = "DATASET_UNRESOLVED"
    LEGACY_JOINT_MODEL_AUDIT_REQUIRED = "LEGACY_JOINT_MODEL_AUDIT_REQUIRED"
    DISABLED = "DISABLED"


class CropRegistryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    crop_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    display_name_en: str
    display_name_ta: str
    aliases: list[str]
    model_status: ModelAvailabilityStatus
    model_version: str | None = None
    architecture: str | None = None
    runtime_path: str | None
    checkpoint_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    supported_classes: list[str]
    crop_enabled: bool
    disease_detection_enabled: bool
    advisory_enabled: bool
    limitation_message_en: str
    limitation_message_ta: str
    official_accuracy_claim: Literal[False]
    field_validation_status: str
    last_verified_at: str | None
    registry_schema_version: Literal["1.0.0"]

    @model_validator(mode="after")
    def enforce_fail_closed_status(self) -> "CropRegistryEntry":
        if self.model_status != ModelAvailabilityStatus.FROZEN_RUNTIME_READY:
            if self.disease_detection_enabled:
                raise ValueError("unready crop cannot enable disease detection")
            if self.runtime_path is not None:
                raise ValueError("unready crop cannot declare a runtime path")
        if not self.crop_enabled and self.disease_detection_enabled:
            raise ValueError("disabled crop cannot enable disease detection")
        return self


class CropRegistryDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    registry_schema_version: Literal["1.0.0"]
    crops: list[CropRegistryEntry]

    @model_validator(mode="after")
    def unique_ids_and_aliases(self) -> "CropRegistryDocument":
        ids = [entry.crop_id for entry in self.crops]
        if len(ids) != len(set(ids)):
            raise ValueError("crop_id values must be unique")
        aliases: dict[str, str] = {}
        for entry in self.crops:
            for raw in [entry.crop_id, *entry.aliases]:
                alias = raw.strip().casefold()
                if not alias or (alias in aliases and aliases[alias] != entry.crop_id):
                    raise ValueError(f"ambiguous crop alias: {raw}")
                aliases[alias] = entry.crop_id
        return self


class CropPublicView(BaseModel):
    crop_id: str
    display_name_en: str
    display_name_ta: str
    model_status: ModelAvailabilityStatus
    crop_enabled: bool
    disease_detection_enabled: bool
    advisory_enabled: bool
    limitation_message_en: str
    limitation_message_ta: str
    official_accuracy_claim: Literal[False]
    field_validation_status: str


class ModelUnavailableResponse(BaseModel):
    status: Literal["MODEL_NOT_AVAILABLE"] = "MODEL_NOT_AVAILABLE"
    crop_id: str
    disease_detection_available: Literal[False] = False
    message_en: str
    message_ta: str
    limitation: ModelAvailabilityStatus
    official_accuracy_claim: Literal[False] = False
