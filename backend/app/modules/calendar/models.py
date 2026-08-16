"""Crop calendar ORM model (docs/DATABASE_SCHEMA.md → Crop Calendar domain).

One row per scheduled farming activity, user- and farm-scoped. Stores stable
localization ``code``s (Tamil-first frontend) plus English title/description as
fallback for logs and future AI. Reminder columns are metadata only in V1 — no
push is scheduled yet (docs: notifications prepared for future FCM).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.calendar.constants import (
    EventStatus,
    Priority,
    WeatherDependency,
)
from app.shared.base_model import (
    GUID,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)


class CalendarEvent(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "crop_calendar_events"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True, nullable=False
    )
    # Reserved for future per-sowing crop-session linkage (docs: future AI).
    crop_session_id: Mapped[uuid.UUID | None] = mapped_column(GUID())

    # Stable identity of the activity, for localization + regeneration idempotency.
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    scheduled_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    day_offset: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    crop: Mapped[str | None] = mapped_column(String(80), index=True)
    season: Mapped[str | None] = mapped_column(String(20))
    growth_stage: Mapped[str] = mapped_column(String(20), nullable=False)

    priority: Mapped[str] = mapped_column(String(10), default=Priority.MEDIUM.value, nullable=False)
    status: Mapped[str] = mapped_column(
        String(10), default=EventStatus.PENDING.value, nullable=False, index=True
    )
    weather_dependency: Mapped[str] = mapped_column(
        String(20), default=WeatherDependency.NONE.value, nullable=False
    )

    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Reminder metadata for future FCM scheduling (no push in V1).
    reminder_hour: Mapped[int | None] = mapped_column(Integer)

    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    registry_version: Mapped[str | None] = mapped_column(String(40))
    registry_content_hash: Mapped[str | None] = mapped_column(String(64))
    registry_verification_status: Mapped[str | None] = mapped_column(String(24))
    registry_source_reference: Mapped[str | None] = mapped_column(String(240))
