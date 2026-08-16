from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class FarmTeamRole(StrEnum):
    MANAGER = "manager"
    FIELD_WORKER = "field_worker"
    AGRONOMIST = "agronomist"
    OBSERVER = "observer"


class FarmTeamMemberCreate(BaseModel):
    phone_number: str = Field(min_length=10, max_length=16)
    role: FarmTeamRole

    @field_validator("phone_number")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        normalized = value.replace(" ", "").replace("-", "")
        if not normalized.startswith("+") or not normalized[1:].isdigit():
            raise ValueError("Phone number must use international format, for example +91…")
        return normalized


class FarmTeamMemberOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    phone_number: str
    role: FarmTeamRole
    created_at: datetime
    test_mode: bool = True
    grants_farm_data_access: bool = False
