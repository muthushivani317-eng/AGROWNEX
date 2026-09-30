"""Farmer request/response schemas (docs/API_CONTRACT.md → FARMER MODULE)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.auth.models import User
from app.modules.auth.profile_models import (
    FarmerLanguage,
    FarmerPreference,
    FarmerProfile,
)
from app.modules.farm_profile.schemas import OnboardingProfileFields, OnboardingProfileOut
from app.modules.farmers.constants import LANGUAGE_PATTERN


# --------------------------------------------------------------------------- #
# /farmers/me
# --------------------------------------------------------------------------- #
class FarmerMeUpdate(OnboardingProfileFields):
    """Editable farmer profile fields (docs/USER_FLOWS.md → Profile flow)."""

    full_name: str = Field(min_length=2, max_length=120)
    gender: str | None = Field(default=None, max_length=20)
    language: str = Field(default="ta", pattern=LANGUAGE_PATTERN)
    district: str | None = Field(default=None, max_length=80)
    block: str | None = Field(default=None, max_length=80)
    village: str | None = Field(default=None, max_length=80)
    experience_years: int | None = Field(default=None, ge=0, le=80)
    education: str | None = Field(default=None, max_length=80)
    profile_photo: str | None = Field(default=None, max_length=512)
    preferred_crops: list[str] = Field(default_factory=list)


class FarmerMeOut(OnboardingProfileOut):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str | None
    gender: str | None
    language: str
    district: str | None
    block: str | None
    village: str | None
    profile_photo: str | None
    experience_years: int | None
    education: str | None
    primary_crop: str | None
    secondary_crop: str | None
    preferred_crops: list[str]
    phone_number: str | None
    email: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_profile(cls, profile: FarmerProfile, user: User) -> FarmerMeOut:
        """Combine the profile row with the owner's contact details."""
        crops = [c for c in (profile.primary_crop, profile.secondary_crop) if c]
        return cls(
            id=profile.id,
            user_id=profile.user_id,
            full_name=profile.full_name,
            gender=profile.gender,
            language=profile.language,
            district=profile.district,
            block=profile.block,
            village=profile.village,
            profile_photo=profile.profile_photo,
            experience_years=profile.experience_years,
            education=profile.education,
            primary_crop=profile.primary_crop,
            secondary_crop=profile.secondary_crop,
            preferred_crops=crops,
            phone_number=user.phone_number,
            email=user.email,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
            land_holding_acres=getattr(profile, "land_holding_acres", None),
            farmer_type=getattr(profile, "farmer_type", None),
            landmark=getattr(profile, "landmark", None),
            needs=getattr(profile, "needs", None),
            needs_note=getattr(profile, "needs_note", None),
        )


# --------------------------------------------------------------------------- #
# /farmers/preferences
# --------------------------------------------------------------------------- #
class PreferencesUpdate(BaseModel):
    """Partial update — only the supplied fields are changed."""

    theme: str | None = Field(default=None, pattern="^(system|light|dark)$")
    notifications_enabled: bool | None = None
    voice_enabled: bool | None = None
    preferred_units: str | None = Field(default=None, pattern="^(metric|imperial)$")
    default_crop: str | None = Field(default=None, max_length=80)


class PreferencesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    farmer_id: uuid.UUID
    theme: str
    notifications_enabled: bool
    voice_enabled: bool
    preferred_units: str
    default_crop: str | None


# --------------------------------------------------------------------------- #
# /farmers/languages
# --------------------------------------------------------------------------- #
class FarmerLanguageIn(BaseModel):
    language_code: str = Field(pattern=LANGUAGE_PATTERN)
    is_default: bool = False


class LanguagesUpdate(BaseModel):
    languages: list[FarmerLanguageIn] = Field(min_length=1)


class FarmerLanguageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    farmer_id: uuid.UUID
    language_code: str
    is_default: bool

    @classmethod
    def from_rows(cls, rows: list[FarmerLanguage]) -> list[FarmerLanguageOut]:
        return [cls.model_validate(row) for row in rows]


def preferences_out(preference: FarmerPreference) -> PreferencesOut:
    return PreferencesOut.model_validate(preference)
