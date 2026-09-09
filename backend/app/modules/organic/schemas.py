from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.organic.constants import CertificationStatus, OrganicFarmMode


class OrganicProfileWrite(BaseModel):
    mode: OrganicFarmMode
    transition_start_date: date | None = None
    goals: list[str] = Field(default_factory=list, max_length=30)
    preferred_practices: list[str] = Field(default_factory=list, max_length=50)
    avoided_input_categories: list[str] = Field(default_factory=list, max_length=50)
    certification_status: CertificationStatus = CertificationStatus.NOT_CLAIMED
    certification_scheme: str | None = Field(default=None, max_length=120)
    certification_identifier: str | None = Field(default=None, max_length=160)
    certificate_issued_on: date | None = None
    certificate_expires_on: date | None = None

    @model_validator(mode="after")
    def validate_claim(self):
        if self.certification_status == CertificationStatus.VERIFIED:
            raise ValueError("Farmers cannot self-assign verified certification")
        if self.certificate_expires_on and self.certificate_issued_on:
            if self.certificate_expires_on < self.certificate_issued_on:
                raise ValueError("certificate_expires_on must not precede certificate_issued_on")
        return self


class OrganicProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    farm_id: uuid.UUID
    mode: str
    transition_start_date: date | None
    goals: list[str]
    preferred_practices: list[str]
    avoided_input_categories: list[str]
    certification_status: str
    certification_scheme: str | None
    certification_identifier: str | None
    certificate_issued_on: date | None
    certificate_expires_on: date | None
    certification_verified_at: datetime | None
    plan_version: int
    created_at: datetime
    updated_at: datetime


class CertificationDocumentCreate(BaseModel):
    object_key: str = Field(min_length=1, max_length=512)
    file_name: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(pattern=r"^(application/pdf|image/(jpeg|png))$")
    file_size: int = Field(gt=0, le=15_000_000)
    sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    upload_receipt: str = Field(pattern=r"^[0-9a-f]{64}$")


class CertificationDocumentOut(BaseModel):
    """Safe metadata view: deliberately omits object_key."""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    file_name: str
    mime_type: str
    file_size: int
    sha256: str
    review_status: str
    created_at: datetime


class OrganicInputOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    slug: str
    category: str
    name_en: str
    name_ta: str
    purpose_en: str
    purpose_ta: str
    guidance: dict
    applicable_crops: list[str]
    applicable_stages: list[str]
    applicable_regions: list[str]
    limitations: dict
    source_organization: str
    document_reference: str
    source_url: str
    source_version: str
    content_hash: str
    reviewed_at: datetime
    effective_from: date | None
    review_due_on: date | None


class SourceActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    source_feature: str
    source_record_id: str
    source_version: str
    action_code: str
    suggestion_time: datetime
    source_verified: bool
    crop_cycle_id: str | None = None


class DiseasePlanStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    order: int
    kind: str
    title_code: str
    requires_expert: bool
    organic_input: OrganicInputOut | None
    source_action: SourceActionOut


class DiseaseOrganicPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    report_id: uuid.UUID
    support_level: str
    treatments_available: bool
    steps: list[DiseasePlanStepOut]


class SoilAmendmentOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    organic_input: OrganicInputOut
    rate_value: float
    rate_unit: str
    calculated_quantity: float | None
    calculated_unit: str | None
    source_action: SourceActionOut


class SoilOrganicMatterPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    farm_id: uuid.UUID
    area_hectares: float | None
    organic_carbon: float | None
    organic_carbon_evidence_type: str
    is_estimate: bool
    options: list[SoilAmendmentOptionOut]


class OrganicFarmSummaryOut(BaseModel):
    farm_id: uuid.UUID
    profile: OrganicProfileOut | None
    certification_status: str | None
    certification_verified: bool
    soil_plan_available: bool
    pending_organic_actions: int
    logbook_entries: int
    weather_advisory_available: bool
    satellite_advisory_available: bool
    traceability_ready: bool
    traceability_batch_count: int
