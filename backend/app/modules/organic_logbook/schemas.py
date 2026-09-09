from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from .models import OrganicPracticeEvidence, OrganicPracticeLogEntry

PracticeType = Literal[
    "amendment", "seed_treatment", "biological_treatment", "botanical_spray",
    "trap", "mechanical_weeding", "mulching", "green_manure", "crop_rotation",
    "irrigation_drainage", "scouting", "harvest", "custom",
]
OutcomeStatus = Literal["not_reported", "improved", "no_change", "worse", "unknown"]


class OrganicEvidenceIn(BaseModel):
    evidence_type: Literal["photo", "voice_note", "receipt", "document", "other"]
    storage_ref: str = Field(min_length=1, max_length=512)
    content_hash: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")
    mime_type: str | None = Field(default=None, max_length=80)
    captured_at: datetime | None = None
    retention_consent: bool = False


class OrganicLogCreateIn(BaseModel):
    farm_id: uuid.UUID
    crop_cycle_id: str | None = Field(default=None, max_length=80)
    action_workflow_id: uuid.UUID | None = None
    daily_task_id: uuid.UUID | None = None
    practice_type: PracticeType
    practice_code: str = Field(min_length=1, max_length=120)
    input_reference: str | None = Field(default=None, max_length=120)
    quantity: float | None = Field(default=None, gt=0)
    quantity_unit: str | None = Field(default=None, max_length=30)
    treated_area_hectares: float | None = Field(default=None, gt=0)
    occurred_at: datetime
    note: str | None = Field(default=None, max_length=2000)
    outcome_status: OutcomeStatus = "not_reported"
    idempotency_key: str = Field(min_length=8, max_length=100)
    evidence: list[OrganicEvidenceIn] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def quantity_has_unit(self):
        if bool(self.quantity) != bool(self.quantity_unit):
            raise ValueError("QUANTITY_AND_UNIT_REQUIRED_TOGETHER")
        return self


class OrganicEvidenceOut(BaseModel):
    id: uuid.UUID
    evidence_type: str
    content_hash: str | None
    mime_type: str | None
    captured_at: datetime | None
    retention_consent: bool
    farmer_reported: bool
    expert_reviewed: bool

    @classmethod
    def from_row(cls, row: OrganicPracticeEvidence):
        return cls.model_validate(row, from_attributes=True)


class OrganicLogOut(BaseModel):
    id: uuid.UUID
    farm_id: uuid.UUID
    crop_cycle_id: str | None
    action_workflow_id: uuid.UUID | None
    daily_task_id: uuid.UUID | None
    practice_type: str
    practice_code: str
    input_reference: str | None
    quantity: float | None
    quantity_unit: str | None
    treated_area_hectares: float | None
    occurred_at: datetime
    note: str | None
    outcome_status: str
    source_feature: str
    source_record_id: str
    source_version: str
    source_verified: bool
    verification_status: str
    expert_reviewed: bool
    evidence: list[OrganicEvidenceOut]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: OrganicPracticeLogEntry):
        return cls.model_validate(row, from_attributes=True)
