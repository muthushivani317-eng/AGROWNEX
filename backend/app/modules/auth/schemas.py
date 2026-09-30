"""Auth request/response schemas (docs/API_CONTRACT.md → AUTH MODULE)."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.modules.farm_profile.schemas import OnboardingProfileFields, OnboardingProfileOut


# --- Requests ---
class OtpSendRequest(BaseModel):
    phone_number: str = Field(min_length=8, max_length=20)


class SocialLoginRequest(BaseModel):
    """Exchange a verified Firebase ID token (phone/Google/Apple) for a session."""

    id_token: str = Field(min_length=10)
    device_name: str | None = None
    device_type: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=10)


class ProfileUpdateRequest(OnboardingProfileFields):
    full_name: str = Field(min_length=2, max_length=120)
    language: str = Field(default="ta", pattern="^(ta|en)$")
    district: str | None = Field(default=None, max_length=80)
    block: str | None = Field(default=None, max_length=80)
    village: str | None = Field(default=None, max_length=80)
    experience_years: int | None = Field(default=None, ge=0, le=80)
    annual_income: int | None = Field(default=None, ge=0, le=100_000_000)
    profile_photo: str | None = Field(default=None, max_length=512)
    preferred_crops: list[str] = Field(default_factory=list)


# --- Responses ---
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    firebase_uid: str
    # Stable, farmer-facing reference code (e.g. "AGF-000123456"). This is
    # what a farmer gives an FPO/organization so it can request read access
    # to their data (see organic_mvp.partner_router) — surfaced here so it
    # reaches the mobile app through /auth/otp/verify and /auth/profile.
    farmer_ref: str
    phone_number: str | None
    email: str | None
    is_phone_verified: bool
    is_email_verified: bool
    status: str


class OtpSendResponse(BaseModel):
    sent: bool
    expires_in: int


class ProfileOut(OnboardingProfileOut):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str | None
    language: str
    district: str | None
    block: str | None
    village: str | None
    profile_photo: str | None
    experience_years: int | None
    annual_income: int | None
    primary_crop: str | None
    secondary_crop: str | None


class SessionOut(BaseModel):
    user: UserOut
    profile: ProfileOut | None
    roles: list[str]
    refresh_token: str
    session_id: uuid.UUID
