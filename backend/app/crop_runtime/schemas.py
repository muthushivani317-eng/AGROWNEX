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


class ClassSpecificGate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confidence_threshold: float = Field(ge=0, le=1)
    margin_threshold: float = Field(ge=0, le=1)


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
    deployment_zip_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    deployment_status: str | None = None
    supported_classes: list[str]
    expected_temperature: float | None = Field(default=None, gt=0)
    expected_class_gates: dict[str, ClassSpecificGate] | None = None
    thresholds_filename: str = Field(
        default="selected_thresholds.json",
        pattern=r"^[A-Za-z0-9_.-]+\.json$",
    )
    frozen_fallback: Literal["ABSTAIN"] | None = None
    crop_enabled: bool
    disease_detection_enabled: bool
    advisory_enabled: bool
    pilot_inference_eligible: bool = False
    general_farmer_inference_authorized: bool | None = None
    limitation_message_en: str
    limitation_message_ta: str
    official_accuracy_claim: Literal[False]
    expert_verified: Literal[False] = False
    tamil_nadu_field_validated: Literal[False] = False
    field_validation_status: str
    last_verified_at: str | None
    registry_schema_version: Literal["1.0.0"]

    @model_validator(mode="after")
    def enforce_fail_closed_status(self) -> CropRegistryEntry:
        if self.model_status != ModelAvailabilityStatus.FROZEN_RUNTIME_READY:
            if self.disease_detection_enabled:
                raise ValueError("unready crop cannot enable disease detection")
            if self.runtime_path is not None:
                raise ValueError("unready crop cannot declare a runtime path")
        if not self.crop_enabled and self.disease_detection_enabled:
            raise ValueError("disabled crop cannot enable disease detection")
        if self.general_farmer_inference_authorized is True:
            raise ValueError("registry cannot pre-authorize farmer inference")
        if self.expected_class_gates is not None and list(
            self.expected_class_gates
        ) != self.supported_classes:
            raise ValueError("class-specific gate order must match supported classes")
        return self


class CropRegistryDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    registry_schema_version: Literal["1.0.0"]
    crops: list[CropRegistryEntry]

    @model_validator(mode="after")
    def unique_ids_and_aliases(self) -> CropRegistryDocument:
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
