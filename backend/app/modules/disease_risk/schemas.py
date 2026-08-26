from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Lifecycle = Literal[
    "UNVERIFIED",
    "PENDING_REVIEW",
    "VERIFIED",
    # Compiled from a real, cited public agronomic/epidemiological source
    # (e.g. a KVK/TNAU/ICAR advisory bulletin on weather-triggered disease
    # risk) but not personally reviewed by an independent agronomist for
    # AgrowAI -- mirrors app.modules.calendar.registry.ScheduleStatus's
    # SOURCED_PUBLIC_REFERENCE. `source_references` must still be genuine,
    # real, checkable documents; this status only changes the "who signed
    # off" claim shown to the farmer, never the "is this made up" answer.
    "SOURCED_PUBLIC_REFERENCE",
    "SUSPENDED",
    "REJECTED",
    "EXPIRED",
]

# Statuses that make a rule pack live/executable for a farmer.
LIVE_LIFECYCLE_STATUSES = frozenset({"VERIFIED", "SOURCED_PUBLIC_REFERENCE"})


class RiskStatus(StrEnum):
    NO_VERIFIED_RULE_AVAILABLE = "NO_VERIFIED_RULE_AVAILABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    CONDITIONS_NOT_MET = "CONDITIONS_NOT_MET"
    RISK_CONDITIONS_PRESENT = "RISK_CONDITIONS_PRESENT"


class RiskEvaluateRequest(BaseModel):
    farm_id: uuid.UUID
    crop_cycle_id: str | None = Field(default=None, max_length=80)
    idempotency_key: str = Field(min_length=8, max_length=100)


class RiskAlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    farm_id: uuid.UUID
    crop: str
    disease_key: str | None
    status: str
    risk_level: str | None
    confidence: str
    weather_factors: list[str]
    weather_source: str
    weather_observed_at: datetime | None
    crop_stage: str | None
    generated_at: datetime
    valid_until: datetime | None
    rule_version: str | None
    rule_verification_status: str
    farmer_message_key: str
    evidence: dict[str, Any]
    missing_inputs: list[str]
    acknowledged_at: datetime | None
    cached: bool = False


class RiskListOut(BaseModel):
    items: list[RiskAlertOut]
    total: int
    active_verified_rule_count: int


class RuleCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    variable: str = Field(min_length=1, max_length=80)
    operator: Literal["gt", "gte", "lt", "lte", "eq"]
    value: float


class RulePack(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"]
    pack_id: str = Field(min_length=1, max_length=100)
    version: str = Field(min_length=1, max_length=40)
    crop_id: str = Field(pattern=r"^[a-z0-9_]+$")
    disease_id: str = Field(pattern=r"^[a-z0-9_]+$")
    regions: list[str] = Field(min_length=1)
    seasons: list[str] = Field(min_length=1)
    confirmed_stages: list[str] = Field(min_length=1)
    required_weather_variables: list[str] = Field(min_length=1)
    observation_window_hours: int = Field(gt=0, le=720)
    forecast_window_hours: int = Field(gt=0, le=720)
    conditions: list[RuleCondition] = Field(min_length=1)
    minimum_data_completeness: float = Field(ge=0, le=1)
    maximum_weather_age_hours: int = Field(gt=0, le=168)
    cached_weather_allowed: bool
    alert_title_key: str = Field(min_length=1)
    alert_explanation_key: str = Field(min_length=1)
    source_references: list[str] = Field(min_length=1)
    reviewer_id: str = Field(min_length=1)
    approval_status: Lifecycle
    approved_at: datetime | None
    review_expires_at: datetime
    cooldown_hours: int = Field(gt=0, le=720)
    alert_expiry_hours: int = Field(gt=0, le=168)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def verified_has_approval(self):
        if self.approval_status in LIVE_LIFECYCLE_STATUSES and self.approved_at is None:
            raise ValueError("LIVE_PACK_REQUIRES_APPROVAL_DATE")
        return self

    def expected_hash(self) -> str:
        payload = self.model_dump(mode="json", exclude={"content_hash"})
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()
