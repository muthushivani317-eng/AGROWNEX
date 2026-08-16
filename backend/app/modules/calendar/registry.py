from __future__ import annotations

import hashlib
import json
from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class ScheduleStatus(StrEnum):
    UNVERIFIED = "UNVERIFIED"
    EXPERT_REVIEW_PENDING = "EXPERT_REVIEW_PENDING"
    VERIFIED = "VERIFIED"
    SUSPENDED = "SUSPENDED"
    DISABLED = "DISABLED"
    REJECTED = "REJECTED"


class VerifiedActivity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=60)
    activity_type: str = Field(min_length=1, max_length=40)
    label_key: str = Field(pattern=r"^calendar\.verified\.[a-z0-9_.-]+$")
    description_key: str = Field(pattern=r"^calendar\.verified\.[a-z0-9_.-]+$")
    day_offset: int = Field(ge=-60, le=730)
    notification_offset_days: int | None = Field(default=None, ge=0, le=30)
    notification_eligible: bool = False
    priority: str = Field(default="medium", pattern="^(low|medium|high)$")
    weather_dependency: str = Field(default="none", pattern="^(none|irrigation|spraying)$")


class VerifiedStage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=40)
    label_key: str = Field(pattern=r"^calendar\.stages\.[a-z0-9_.-]+$")
    start_offset: int = Field(ge=0, le=730)
    end_offset: int = Field(ge=0, le=730)
    activities: list[VerifiedActivity] = Field(default_factory=list)

    @model_validator(mode="after")
    def valid_window(self) -> VerifiedStage:
        if self.end_offset < self.start_offset:
            raise ValueError("stage end must not precede start")
        return self


class CropStageSchedule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    canonical_crop_id: str = Field(pattern=r"^[a-z0-9_]+$")
    aliases: list[str] = Field(default_factory=list)
    variety_or_duration_group: str | None = None
    stages: list[VerifiedStage] = Field(min_length=1)
    geographic_limitations: list[str] = Field(min_length=1)
    season_limitations: list[str] = Field(min_length=1)
    source_organization: str = Field(min_length=1)
    document_reference: str = Field(min_length=1)
    reviewer: str = Field(min_length=1)
    approval_date: date
    review_date: date
    version: str = Field(min_length=1)
    status: ScheduleStatus
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def active_evidence(self) -> CropStageSchedule:
        if self.status == ScheduleStatus.VERIFIED and self.review_date < date.today():
            raise ValueError("verified schedule review date has expired")
        return self


def schedule_hash(payload: dict[str, Any]) -> str:
    canonical = {k: v for k, v in payload.items() if k != "content_hash"}
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


class CropStageRegistry:
    def __init__(self, entries: list[dict[str, Any]] | None = None) -> None:
        self._active: dict[str, CropStageSchedule] = {}
        self._aliases: dict[str, str] = {}
        self.review_entries: list[dict[str, Any]] = []
        for raw in entries or []:
            self.review_entries.append(raw)
            try:
                entry = CropStageSchedule.model_validate(raw)
            except ValidationError:
                continue
            if entry.content_hash != schedule_hash(raw) or entry.status != ScheduleStatus.VERIFIED:
                continue
            canonical = entry.canonical_crop_id
            self._active[canonical] = entry
            for alias in [canonical, *entry.aliases]:
                normalized = alias.strip().lower().replace(" ", "_")
                if normalized:
                    self._aliases[normalized] = canonical

    def resolve(self, crop: str | None) -> CropStageSchedule | None:
        if not crop:
            return None
        normalized = crop.strip().lower().replace(" ", "_")
        canonical = self._aliases.get(normalized)
        return self._active.get(canonical) if canonical else None

    @property
    def active_count(self) -> int:
        return len(self._active)

    @property
    def unverified_count(self) -> int:
        return sum(
            1
            for raw in self.review_entries
            if raw.get("status") in {
                ScheduleStatus.UNVERIFIED.value,
                ScheduleStatus.EXPERT_REVIEW_PENDING.value,
            }
        )


# No repository schedule currently has documented expert verification.
ACTIVE_CROP_STAGE_REGISTRY = CropStageRegistry()
