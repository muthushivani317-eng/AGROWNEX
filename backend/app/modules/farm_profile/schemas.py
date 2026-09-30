"""Onboarding v2 request/response shapes (Profile, Crops and Needs steps)."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.farm_profile.catalog import CATEGORIES, FARMER_TYPES, ITEMS, NEEDS, OTHER_CODE, UNITS

MAX_ITEMS = 60


class OnboardingProfileFields(BaseModel):
    """Optional profile fields added by the new onboarding.

    Only fields the client actually sends are written, so older app builds
    that PUT the profile without them never wipe what a newer build saved.
    """

    land_holding_acres: float | None = Field(default=None, ge=0, le=10_000)
    farmer_type: str | None = Field(default=None, max_length=30)
    landmark: str | None = Field(default=None, max_length=160)
    needs: list[str] | None = Field(default=None, max_length=len(NEEDS))
    needs_note: str | None = Field(default=None, max_length=300)

    @field_validator("farmer_type")
    @classmethod
    def _farmer_type(cls, value: str | None) -> str | None:
        if value is not None and value not in FARMER_TYPES:
            raise ValueError(f"farmer_type must be one of: {', '.join(FARMER_TYPES)}")
        return value

    @field_validator("needs")
    @classmethod
    def _needs(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        unknown = [code for code in value if code not in NEEDS]
        if unknown:
            raise ValueError(f"Unknown needs: {', '.join(unknown)}")
        return list(dict.fromkeys(value))

    @field_validator("landmark", "needs_note")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        return (value.strip() or None) if isinstance(value, str) else value


ONBOARDING_FIELDS = tuple(OnboardingProfileFields.model_fields)


class OnboardingProfileOut(BaseModel):
    land_holding_acres: float | None = None
    farmer_type: str | None = None
    landmark: str | None = None
    needs: list[str] | None = None
    needs_note: str | None = None


class FarmItemIn(BaseModel):
    item_code: str = Field(max_length=60)
    category: str | None = Field(default=None, max_length=30)
    custom_name: str | None = Field(default=None, max_length=80)
    harvest_months: list[int] = Field(default_factory=list, max_length=12)
    approx_quantity: float | None = Field(default=None, ge=0, le=10_000_000)
    unit: str | None = Field(default=None, max_length=16)
    area_acres: float | None = Field(default=None, ge=0, le=10_000)
    available_for_sale: bool = False

    @field_validator("harvest_months")
    @classmethod
    def _months(cls, value: list[int]) -> list[int]:
        if any(m < 1 or m > 12 for m in value):
            raise ValueError("harvest_months must be 1-12")
        return sorted(set(value))

    @model_validator(mode="after")
    def _check(self) -> FarmItemIn:
        if self.item_code == OTHER_CODE:
            if not self.custom_name or not self.custom_name.strip():
                raise ValueError("custom_name is required for 'other' items")
            if self.category not in CATEGORIES:
                raise ValueError(f"category must be one of: {', '.join(CATEGORIES)}")
            self.custom_name = " ".join(self.custom_name.split())
        else:
            item = ITEMS.get(self.item_code)
            if item is None:
                raise ValueError(f"Unknown item_code: {self.item_code}")
            self.category = item["category"]
            self.custom_name = None
            self.unit = self.unit or item["default_unit"]
        if self.unit is not None and self.unit not in UNITS:
            raise ValueError(f"unit must be one of: {', '.join(UNITS)}")
        if self.approx_quantity is not None and self.unit is None:
            raise ValueError("unit is required with approx_quantity")
        return self


class FarmItemsIn(BaseModel):
    items: list[FarmItemIn] = Field(default_factory=list, max_length=MAX_ITEMS)

    @model_validator(mode="after")
    def _unique(self) -> FarmItemsIn:
        keys = [(i.item_code, (i.custom_name or "").lower()) for i in self.items]
        if len(keys) != len(set(keys)):
            raise ValueError("Each item can be listed only once")
        return self


class FarmItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    item_code: str
    category: str
    custom_name: str | None
    name: str = ""
    name_ta: str | None = None
    harvest_months: list[int]
    approx_quantity: float | None
    unit: str | None
    area_acres: float | None
    available_for_sale: bool


class JoinRequestIn(BaseModel):
    """Farmer asks to join an FPO/KVK; they consent to share by sending it."""

    consent: bool = Field(description="Must be true: the farmer agreed to share profile and crops.")

    @field_validator("consent")
    @classmethod
    def _consent(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Consent is required to join.")
        return value
