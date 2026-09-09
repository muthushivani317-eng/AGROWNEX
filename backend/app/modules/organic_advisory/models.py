from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import GUID, Base, TimestampMixin, UUIDMixin


class OrganicWeatherSnapshot(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organic_weather_snapshots"

    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), index=True)
    farm_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("farms.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    provider_fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False)


class OrganicActionReschedule(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organic_action_reschedules"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_organic_reschedule_idempotency"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), index=True)
    farm_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("farms.id"), index=True)
    action_workflow_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("action_workflows.id"), index=True
    )
    weather_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organic_weather_snapshots.id"), nullable=False
    )
    signal_code: Mapped[str] = mapped_column(String(50), nullable=False)
    prior_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rescheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)


class OrganicNotificationIntent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organic_notification_intents"
    __table_args__ = (
        UniqueConstraint("user_id", "dedup_key", name="uq_organic_notification_intent"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), index=True)
    farm_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("farms.id"), index=True)
    reschedule_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organic_action_reschedules.id"), nullable=False
    )
    dedup_key: Mapped[str] = mapped_column(String(200), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
