"""Requests for organic pilot workflows. All fields represent real user input."""
from __future__ import annotations

import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class PilotSetupIn(BaseModel):
    fpo_id: uuid.UUID | None = None
    fpo_name: str | None = Field(default=None, max_length=180)
    district: str | None = Field(default=None, max_length=80)
    crop_ids: list[str] = Field(default_factory=list, max_length=2)
    agronomist_user_id: uuid.UUID | None = None
    certification_pathway: Literal["pre_certification_trial", "pgs_eligibility_review"] | None = None
    is_test: bool = False


class FpoIn(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    district: str = Field(min_length=2, max_length=80)
    registration_reference: str | None = Field(default=None, max_length=120)
    is_test: bool = False


class EnrollIn(BaseModel):
    farm_id: uuid.UUID
    farmer_user_id: uuid.UUID
    consent_confirmed: bool


class PlotIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    area_hectares: float | None = Field(default=None, gt=0)
    boundary_geojson: dict | None = None


class CropCycleDatesIn(BaseModel):
    """Partial update of a crop cycle's dates (only sent fields change)."""

    sowing_date: date | None = None
    expected_harvest_start: date | None = None
    expected_harvest_end: date | None = None

    @staticmethod
    def check_order(*, sowing_date, expected_harvest_start, expected_harvest_end) -> None:
        from app.core.exceptions import ValidationError

        if expected_harvest_start and expected_harvest_end and expected_harvest_start > expected_harvest_end:
            raise ValidationError("Harvest end must follow harvest start.")
        if sowing_date and expected_harvest_start and sowing_date > expected_harvest_start:
            raise ValidationError("Harvest must follow sowing.")


class CropCycleIn(BaseModel):
    crop_id: str = Field(min_length=1, max_length=80)
    sowing_date: date | None = None
    expected_harvest_start: date | None = None
    expected_harvest_end: date | None = None
    expected_quantity_kg: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def harvest_order(self):
        if self.expected_harvest_start and self.expected_harvest_end and self.expected_harvest_start > self.expected_harvest_end:
            raise ValueError("Harvest end must follow harvest start.")
        if self.sowing_date and self.expected_harvest_start and self.sowing_date > self.expected_harvest_start:
            raise ValueError("Harvest must follow sowing.")
        return self


class ReadinessRulesIn(BaseModel):
    version: str = Field(min_length=1, max_length=60)
    questions: list[dict] = Field(min_length=1)
    scoring: dict


class ReadinessAnswersIn(BaseModel):
    answers: dict[str, str]


class TemplateIn(BaseModel):
    crop_id: str = Field(min_length=1, max_length=80)
    district: str = Field(min_length=1, max_length=80)
    version: str = Field(min_length=1, max_length=60)
    tasks: list[dict] = Field(default_factory=list)


class ReviewIn(BaseModel):
    approved: bool
    note: str | None = Field(default=None, max_length=2000)


class PgsFarmerIn(BaseModel):
    partial_conversion: bool = False
    checklist: dict[str, bool] = Field(default_factory=dict)


class PgsReviewIn(BaseModel):
    requested_state: Literal[
        "pgs_eligibility_review", "regional_council_approval_required",
        "pgs_registration_pending", "pgs_green_under_conversion",
        "pgs_organic", "non_compliance_review",
    ]
    regional_council_approval_ref: str | None = Field(default=None, max_length=180)
    certificate_id: str | None = Field(default=None, max_length=160)
    issuing_authority: str | None = Field(default=None, max_length=180)
    valid_from: date | None = None
    valid_to: date | None = None
    certificate_document_id: uuid.UUID | None = None
    verified_evidence: bool = False
    major_non_compliance: bool = False
    non_compliance_note: str | None = Field(default=None, max_length=2000)


class AppraisalIn(BaseModel):
    scheduled_on: date
    peer_user_id: uuid.UUID


class AppraisalCompleteIn(BaseModel):
    findings: dict
    complete: bool = True
