from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ConsentDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: str = Field(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9._:-]+$")
    locale: Literal["en", "ta"]
    notice_version: Literal["2026-08-v1"]


class ConsentStateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    purpose: Literal[
        "optional_product_analytics", "buyer_contact_sharing", "marketing", "precise_location"
    ]
    granted: bool
    version: int
    policy_version: str | None
    notice_hash: str | None
    channel: str | None
    locale: str | None
    decided_at: datetime | None


class CoreProcessingOut(BaseModel):
    purpose: Literal["required_service"] = "required_service"
    legal_basis: Literal["service_contract"] = "service_contract"
    withdrawable_as_consent: Literal[False] = False


class ConsentOverviewOut(BaseModel):
    core_processing: CoreProcessingOut
    consents: list[ConsentStateOut]
