"""Farmer profile models (docs/DATABASE_SCHEMA.md → Farmer domain).

Profile entities required for the authentication/profile-setup flow:
farmer_profiles · farmer_preferences · farmer_languages. Farm tables are NOT
created here — they belong to the Farm Registration module.
"""
from __future__ import annotations

import uuid

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import (
    GUID,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)


class FarmerProfile(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Main farmer profile (docs/DATABASE_SCHEMA.md → farmer_profiles)."""

    __tablename__ = "farmer_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), unique=True, index=True, nullable=False
    )
    full_name: Mapped[str | None] = mapped_column(String(120))
    gender: Mapped[str | None] = mapped_column(String(20))
    language: Mapped[str] = mapped_column(String(5), default="ta", nullable=False)
    district: Mapped[str | None] = mapped_column(String(80), index=True)
    block: Mapped[str | None] = mapped_column(String(80), index=True)
    village: Mapped[str | None] = mapped_column(String(80), index=True)
    profile_photo: Mapped[str | None] = mapped_column(String(512))
    experience_years: Mapped[int | None] = mapped_column(Integer)
    annual_income: Mapped[int | None] = mapped_column(Integer)
    education: Mapped[str | None] = mapped_column(String(80))
    primary_crop: Mapped[str | None] = mapped_column(String(80), index=True)
    secondary_crop: Mapped[str | None] = mapped_column(String(80))
    # Onboarding v2 (Profile + Needs steps). Codes come from
    # app.modules.farm_profile.catalog.
    land_holding_acres: Mapped[float | None] = mapped_column(Float)
    farmer_type: Mapped[str | None] = mapped_column(String(30))
    landmark: Mapped[str | None] = mapped_column(String(160))
    needs: Mapped[list | None] = mapped_column(JSON)
    needs_note: Mapped[str | None] = mapped_column(String(300))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    wants_fpo_support: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    wants_kvk_support: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class FarmerPreference(UUIDMixin, TimestampMixin, Base):
    """User settings (docs/DATABASE_SCHEMA.md → farmer_preferences)."""

    __tablename__ = "farmer_preferences"

    farmer_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("farmer_profiles.id"),
        unique=True,
        index=True,
        nullable=False,
    )
    theme: Mapped[str] = mapped_column(String(10), default="system", nullable=False)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    voice_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    preferred_units: Mapped[str] = mapped_column(String(20), default="metric")
    default_crop: Mapped[str | None] = mapped_column(String(80))


class FarmerLanguage(UUIDMixin, TimestampMixin, Base):
    """Farmer language list (docs/DATABASE_SCHEMA.md → farmer_languages)."""

    __tablename__ = "farmer_languages"

    farmer_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farmer_profiles.id"), index=True, nullable=False
    )
    language_code: Mapped[str] = mapped_column(String(5), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
