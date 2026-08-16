from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class EquipmentType(StrEnum):
    TRACTOR = "tractor"
    TILLER = "tiller"
    HARVESTER = "harvester"
    SPRAYER = "sprayer"
    PUMP = "pump"
    OTHER = "other"


class EquipmentListingCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    equipment_type: EquipmentType
    district: str | None = Field(default=None, max_length=80)
    description: str | None = Field(default=None, max_length=1000)


class EquipmentListingOut(EquipmentListingCreate):
    id: uuid.UUID
    owner_user_id: uuid.UUID
    status: str
    created_at: datetime
    test_mode: bool = True
    payments_supported: bool = False


class EquipmentRequestCreate(BaseModel):
    farm_id: uuid.UUID
    start_date: date
    end_date: date
    purpose: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def valid_window(self):
        if self.end_date < self.start_date:
            raise ValueError("End date must be on or after start date")
        return self


class EquipmentDecision(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    note: str | None = Field(default=None, max_length=500)


class EquipmentRequestOut(BaseModel):
    id: uuid.UUID
    listing_id: uuid.UUID
    equipment_name: str
    requester_user_id: uuid.UUID
    farm_id: uuid.UUID
    start_date: date
    end_date: date
    purpose: str | None
    status: str
    decision_note: str | None
    created_at: datetime
    test_mode: bool = True
    payment_status: str = "not_supported"
    can_decide: bool = False
    is_requester: bool = False
