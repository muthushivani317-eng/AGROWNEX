"""Crop Growth Monitor ORM models (docs/DATABASE_SCHEMA.md → Crop Growth).

Four tables map the module's task spec:

* ``crop_growth_sessions``  — one monitored crop on one farm over one season.
* ``crop_growth_images``    — each uploaded photo (image + metadata snapshot).
* ``crop_growth_analysis``  — the AI observation for one image (nullable disease
                              / nutrient results reserved for future models).
* ``crop_growth_timelines`` — the Week 1 → Week N roll-up that drives the timeline.

Stage/vigour store stable codes; the Tamil-first frontend localizes them and the
English summary is kept as a fallback for logs and future AI.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.growth.constants import (
    DEFAULT_LANGUAGE,
    GrowthStage,
    PlantVigor,
    RiskLevel,
    SessionStatus,
)
from app.shared.base_model import (
    GUID,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)


class CropGrowthSession(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "crop_growth_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True, nullable=False
    )
    crop: Mapped[str | None] = mapped_column(String(80), index=True)
    variety: Mapped[str | None] = mapped_column(String(80))
    title: Mapped[str | None] = mapped_column(String(160))
    sowing_date: Mapped[date | None] = mapped_column(Date)

    status: Mapped[str] = mapped_column(
        String(12), default=SessionStatus.ACTIVE.value, nullable=False, index=True
    )
    current_growth_stage: Mapped[str] = mapped_column(
        String(20), default=GrowthStage.UNKNOWN.value, nullable=False
    )
    latest_health_score: Mapped[int | None] = mapped_column(Integer)
    latest_risk_level: Mapped[str | None] = mapped_column(String(12))
    image_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class CropGrowthImage(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "crop_growth_images"

    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("crop_growth_sessions.id"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True
    )

    image_url: Mapped[str] = mapped_column(String(512), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(512))
    capture_method: Mapped[str] = mapped_column(String(20), default="gallery")

    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    week_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    weather_snapshot: Mapped[dict | None] = mapped_column(JSON)
    image_quality: Mapped[dict | None] = mapped_column(JSON)
    notes: Mapped[str | None] = mapped_column(Text)


class CropGrowthAnalysis(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "crop_growth_analysis"

    image_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("crop_growth_images.id"),
        index=True,
        unique=True,
        nullable=False,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("crop_growth_sessions.id"), index=True, nullable=False
    )

    growth_stage: Mapped[str] = mapped_column(
        String(20), default=GrowthStage.UNKNOWN.value, nullable=False
    )
    plant_vigor: Mapped[str] = mapped_column(
        String(12), default=PlantVigor.UNKNOWN.value, nullable=False
    )
    health_score: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[int | None] = mapped_column(Integer)

    leaf_color_observations: Mapped[list | None] = mapped_column(JSON)
    visible_abnormalities: Mapped[list | None] = mapped_column(JSON)
    changes_from_previous: Mapped[list | None] = mapped_column(JSON)
    recommendations: Mapped[list | None] = mapped_column(JSON)

    # Reserved, nullable slots for future models (docs: future compatibility).
    disease_result: Mapped[dict | None] = mapped_column(JSON)
    nutrient_result: Mapped[dict | None] = mapped_column(JSON)

    needs_expert_review: Mapped[bool] = mapped_column(Boolean, default=False)
    growth_summary_tamil: Mapped[str | None] = mapped_column(Text)
    growth_summary_english: Mapped[str | None] = mapped_column(Text)

    model_used: Mapped[str | None] = mapped_column(String(60))
    raw_response: Mapped[dict | None] = mapped_column(JSON)
    language: Mapped[str] = mapped_column(
        String(5), default=DEFAULT_LANGUAGE, nullable=False
    )


class CropGrowthTimeline(UUIDMixin, TimestampMixin, Base):
    """One entry per upload — the ordered Week 1 → Week N growth history."""

    __tablename__ = "crop_growth_timelines"

    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("crop_growth_sessions.id"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    image_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("crop_growth_images.id"), nullable=False
    )

    week_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    growth_stage: Mapped[str] = mapped_column(
        String(20), default=GrowthStage.UNKNOWN.value, nullable=False
    )
    health_score: Mapped[int | None] = mapped_column(Integer)
    # Health change vs the previous timeline entry (positive = improving).
    health_delta: Mapped[int | None] = mapped_column(Integer)
    risk_level: Mapped[str] = mapped_column(
        String(12), default=RiskLevel.LOW.value, nullable=False
    )
    summary: Mapped[str | None] = mapped_column(Text)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
