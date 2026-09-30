"""Onboarding v2 request/response shapes (Profile, Crops and Needs steps)."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.farm_profile.catalog import (
    APP_CATEGORY_ALIASES,
    APP_ITEM_ALIASES,
    APP_UNIT_ALIASES,
    CATEGORIES,
    FARMER_TYPE_ALIASES,
    FARMER_TYPES,
    ITEMS,
    NEEDS,
    OTHER_CODE,
    UNITS,
)

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
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    wants_fpo_support: bool | None = None
    wants_kvk_support: bool | None = None
    # App onboarding shape; stored in farmer_farm_items (see farm_profile.service).
    farm_products: list[AppFarmProductIn] | None = Field(default=None, max_length=MAX_ITEMS)

    @field_validator("farmer_type", mode="before")
    @classmethod
    def _farmer_type(cls, value: str | None) -> str | None:
        value = FARMER_TYPE_ALIASES.get(value, value) if isinstance(value, str) else value
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


# Scalar columns copied straight onto FarmerProfile (farm_products is separate;
# the wants_* flags are non-null so None means "not sent").
ONBOARDING_FIELDS = tuple(name for name in OnboardingProfileFields.model_fields if name != "farm_products")


class AppFarmProductIn(BaseModel):
    """One product as the app's onboarding sends it (PUT /farmers/me)."""

    product_id: str = Field(min_length=1, max_length=80)
    category: str = Field(min_length=1, max_length=40)
    expected_harvest_month: str | None = Field(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    approximate_quantity: float | None = Field(default=None, ge=0, le=10_000_000)
    unit: str | None = Field(default=None, max_length=16)
    available_for_sale: bool = False

    def to_item(self) -> FarmItemIn:
        code = APP_ITEM_ALIASES.get(self.product_id, self.product_id)
        category = APP_CATEGORY_ALIASES.get(self.category, self.category)
        unit = APP_UNIT_ALIASES.get(self.unit, self.unit) if self.unit else None
        if code in ITEMS:
            if unit == "nos" and ITEMS[code]["default_unit"] == "head":
                unit = "head"
            if unit is not None and unit not in UNITS:
                unit = None
            return FarmItemIn(
                item_code=code,
                harvest_months=[int(self.expected_harvest_month[5:7])] if self.expected_harvest_month else [],
                approx_quantity=self.approximate_quantity if unit or self.approximate_quantity is None else None,
                unit=unit,
                available_for_sale=self.available_for_sale,
            )
        return FarmItemIn(
            item_code=OTHER_CODE,
            category=category if category in CATEGORIES else "other_products",
            custom_name=self.product_id.replace("_", " ")[:80],
            harvest_months=[int(self.expected_harvest_month[5:7])] if self.expected_harvest_month else [],
            approx_quantity=self.approximate_quantity if unit in UNITS else None,
            unit=unit if unit in UNITS else None,
            available_for_sale=self.available_for_sale,
        )


class AppFarmProductOut(BaseModel):
    product_id: str
    category: str
    expected_harvest_month: str | None = None
    approximate_quantity: float | None = None
    unit: str | None = None
    available_for_sale: bool = False


class OnboardingProfileOut(BaseModel):
    land_holding_acres: float | None = None
    farmer_type: str | None = None
    landmark: str | None = None
    needs: list[str] | None = None
    needs_note: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    wants_fpo_support: bool = False
    wants_kvk_support: bool = False
    farm_products: list[AppFarmProductOut] = Field(default_factory=list)


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


OnboardingProfileFields.model_rebuild()
