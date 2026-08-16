from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from .models import ActionAuditEvent, ActionWorkflow


class ActionCreateIn(BaseModel):
    farm_id: uuid.UUID
    crop_cycle_id: str | None = Field(default=None, max_length=80)
    source_feature: str = Field(min_length=1, max_length=40)
    source_record_id: str = Field(min_length=1, max_length=100)
    source_version: str = Field(min_length=1, max_length=80)
    action_code: str = Field(min_length=1, max_length=120)
    source_verified: bool = False
    farmer_created: bool = True
    suggestion_time: datetime
    due_at: datetime | None = None
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def safe_source(self):
        if not self.farmer_created:
            raise ValueError("SOURCE_ACTIONS_MUST_BE_REGISTERED_SERVER_SIDE")
        if self.source_verified:
            raise ValueError("FARMER_ACTION_CANNOT_SELF_VERIFY_SOURCE")
        return self


class ActionRespondIn(BaseModel):
    event: Literal["view", "done", "not_done", "defer", "correct", "skip", "unable"]
    expected_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=100)
    request_id: str = Field(min_length=1, max_length=100)
    note: str | None = Field(default=None, max_length=500)
    reason: str | None = Field(default=None, max_length=500)
    evidence_base64: str | None = None
    evidence_mime_type: str | None = None
    retention_consent: bool = False

    @model_validator(mode="after")
    def complete_evidence(self):
        if bool(self.evidence_base64) != bool(self.evidence_mime_type):
            raise ValueError("INCOMPLETE_EVIDENCE")
        if self.evidence_base64 or self.evidence_mime_type or self.retention_consent:
            raise ValueError("EVIDENCE_UPLOAD_NOT_AVAILABLE")
        return self


class ActionOut(BaseModel):
    id: uuid.UUID
    farm_id: uuid.UUID
    crop_cycle_id: str | None
    source_feature: str
    source_record_id: str
    source_version: str
    action_code: str
    source_verified: bool
    farmer_created: bool
    suggestion_time: datetime
    due_at: datetime | None
    expires_at: datetime | None
    status: str
    verification_scope: str
    version: int
    pending_sync: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: ActionWorkflow):
        output = cls.model_validate(row, from_attributes=True)
        if (
            row.expires_at
            and row.expires_at < datetime.now(row.expires_at.tzinfo)
            and row.status in {"suggested", "viewed", "deferred"}
        ):
            output.status = "expired"
        return output


class ActionHistoryOut(BaseModel):
    id: uuid.UUID
    event: str
    prior_status: str | None
    new_status: str
    note: str | None
    reason: str | None
    evidence_hash: str | None
    farmer_reported: bool
    expert_reviewed: bool
    created_at: datetime

    @classmethod
    def from_row(cls, row: ActionAuditEvent):
        return cls.model_validate(row, from_attributes=True)
