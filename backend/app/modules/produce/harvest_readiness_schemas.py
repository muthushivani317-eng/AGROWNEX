from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.produce.models import HarvestReadinessHistory, HarvestReadinessRecord


class HarvestReadinessEvaluateIn(BaseModel):
    farm_id: uuid.UUID
    crop_cycle_id: str = Field(min_length=1, max_length=80)
    farmer_observations: list[str] = Field(default_factory=list, max_length=20)
    weather_freshness: str = Field(pattern="^(live|cached|stale|missing)$")
    idempotency_key: str = Field(min_length=8, max_length=100)


class HarvestReadinessConfirmIn(BaseModel):
    readiness_id: uuid.UUID
    ready: bool
    idempotency_key: str = Field(min_length=8, max_length=100)
    note: str | None = Field(default=None, max_length=500)


class HarvestReadinessOut(BaseModel):
    id: uuid.UUID
    farm_id: uuid.UUID
    crop_cycle_id: str
    state: str
    version: int
    criteria_version: str | None
    evidence_snapshot: dict
    pending_sync: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: HarvestReadinessRecord) -> HarvestReadinessOut:
        return cls.model_validate(row, from_attributes=True)


class HarvestReadinessHistoryOut(BaseModel):
    id: uuid.UUID
    event: str
    prior_state: str | None
    next_state: str
    note: str | None
    farmer_confirmed: bool
    evidence_snapshot: dict
    created_at: datetime

    @classmethod
    def from_row(cls, row: HarvestReadinessHistory) -> HarvestReadinessHistoryOut:
        return cls.model_validate(row, from_attributes=True)
