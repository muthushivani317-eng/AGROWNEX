from __future__ import annotations

import hashlib
import json
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.core.logging import get_logger

logger = get_logger("calendar.registry")


class ScheduleStatus(StrEnum):
    UNVERIFIED = "UNVERIFIED"
    EXPERT_REVIEW_PENDING = "EXPERT_REVIEW_PENDING"
    VERIFIED = "VERIFIED"
    # Compiled from a real, cited public agricultural source (TNAU Agritech
    # Portal, ICAR crop production guide, a state Dept. of Agriculture
    # bulletin, etc.) but not yet personally reviewed by an independent
    # agronomist for AgrowAI specifically -- distinct from VERIFIED so the
    # farmer-facing UI can honestly label the difference rather than implying
    # a review that hasn't happened (product decision, 2026-08-17: show real,
    # cited public-source content rather than nothing, but never blur it with
    # an actual expert sign-off). `source_organization`/`document_reference`
    # must still be the genuine publisher and document -- this status does
    # NOT relax the "no fabricated provenance" rule, only the "who reviewed
    # it" claim.
    SOURCED_PUBLIC_REFERENCE = "SOURCED_PUBLIC_REFERENCE"
    SUSPENDED = "SUSPENDED"
    DISABLED = "DISABLED"
    REJECTED = "REJECTED"


# Statuses that make a schedule live/resolvable for a farmer (as opposed to
# draft/rejected/suspended states that are tracked but never surfaced).
_LIVE_STATUSES = frozenset({ScheduleStatus.VERIFIED, ScheduleStatus.SOURCED_PUBLIC_REFERENCE})


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
    organic_practice: bool = False


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
        if self.status in _LIVE_STATUSES and self.review_date < date.today():
            raise ValueError("live schedule review date has expired")
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
            if entry.content_hash != schedule_hash(raw) or entry.status not in _LIVE_STATUSES:
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

    def coverage(self, crops: list[str]) -> dict[str, str]:
        """Fail-closed coverage audit; absence never falls back to invented content."""
        return {
            crop: ("available" if self.resolve(crop) is not None else "source_pack_required")
            for crop in crops
        }

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


# Where real, expert-reviewed crop-stage schedules live once someone adds them
# (see the README in that directory before adding one -- this is a safety
# gate, not a formality). Every *.json file here is loaded at import time;
# `*.json.example` (the template) is intentionally not picked up.
VERIFIED_SCHEDULES_DIR = Path(__file__).resolve().parent / "data" / "verified_schedules"


def _load_verified_schedule_entries(
    directory: Path = VERIFIED_SCHEDULES_DIR,
) -> list[dict[str, Any]]:
    """Read every *.json file in `directory` as a raw schedule entry.

    A file that isn't valid JSON is skipped with a warning rather than
    crashing app startup -- a typo in one crop's file must not take down
    calendar generation for every other crop. Schema/hash/status validation
    happens later, inside CropStageRegistry's constructor, using the same
    logic either way.
    """
    if not directory.is_dir():
        return []
    entries: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(
                "Skipping unreadable verified schedule file",
                extra={"path": str(path), "error": str(exc)},
            )
            continue
        if not isinstance(raw, dict):
            logger.warning(
                "Skipping verified schedule file: expected a JSON object",
                extra={"path": str(path)},
            )
            continue
        entries.append(raw)
    return entries


# No repository schedule currently has documented expert verification -- see
# app/modules/calendar/data/verified_schedules/README.md. This loads from
# that directory rather than being hardcoded empty, so adding a real,
# reviewed schedule there is enough to bring a crop online; nothing in this
# file needs to change.
ACTIVE_CROP_STAGE_REGISTRY = CropStageRegistry(_load_verified_schedule_entries())
