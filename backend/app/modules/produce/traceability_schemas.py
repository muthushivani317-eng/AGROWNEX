from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class TraceEventType(StrEnum):
    SOWING_RECORDED = "sowing_recorded"
    INPUT_APPLIED = "input_applied"
    HARVESTED = "harvested"
    GRADED = "graded"
    PACKED = "packed"
    STORED = "stored"
    TRANSPORTED = "transported"
    HANDOVER = "handover"


class TraceEventCreate(BaseModel):
    event_type: TraceEventType
    occurred_at: datetime
    location_text: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=1000)
    evidence_url: str | None = Field(default=None, max_length=512)

    @field_validator("occurred_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone")
        return value


class TraceEventOut(BaseModel):
    id: uuid.UUID
    event_type: TraceEventType
    occurred_at: datetime
    location_text: str | None
    notes: str | None
    evidence_url: str | None
    event_hash: str
    created_at: datetime
    declared_by_farmer: bool = True
    independently_verified: bool = False


class TraceTimelineOut(BaseModel):
    batch_id: uuid.UUID
    offer_id: uuid.UUID
    batch_code: str
    events: list[TraceEventOut]
    test_mode: bool = True
    public_certificate: bool = False
    disclaimer: str
