"""Notification ORM models (docs/DATABASE_SCHEMA.md → Notifications domain).

Normalized tables — the event center of AgrowAI:

* ``notifications``              — one stored notification per row (user-scoped,
  optional ``farm_id``). Stores localization keys + a payload (Tamil-first client
  renders them), severity/priority, read/dismissed flags, and delivery/expiry
  timestamps. Notifications are never hard-deleted (docs) — "delete" = *dismiss*.
* ``notification_preferences``   — per-user module + channel opt-outs and the
  minimum-severity gate. One row per user.
* ``notification_delivery_log``  — an audit row per channel delivery attempt
  (docs: "Notification Sent" must be traceable).
* ``notification_templates``     — the rule table materialized in the DB, seeded
  from ``constants.RULES`` so operators can inspect/extend rules without code.
* ``future_notification_queue``  — scheduled notifications not yet due; the engine
  promotes due rows into ``notifications`` on the next sync.

``user_id`` is the farmer (FK ``users.id``) — every module scopes by the
authenticated user, matching the docs' ``farmer_id`` concept.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.notifications.constants import (
    DEFAULT_LANGUAGE,
    Priority,
    Severity,
)
from app.shared.base_model import (
    GUID,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)


class Notification(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        # One live notification per logical event per user (deterministic dedup).
        UniqueConstraint("user_id", "dedup_key", name="uq_notifications_user_dedup"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True
    )

    module: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)

    # Localization keys + payload — the Tamil-first client renders the text.
    title_key: Mapped[str] = mapped_column(String(120), nullable=False)
    message_key: Mapped[str] = mapped_column(String(120), nullable=False)
    payload_json: Mapped[dict | None] = mapped_column(JSON)

    severity: Mapped[str] = mapped_column(
        String(12), default=Severity.INFO.value, nullable=False
    )
    priority: Mapped[str] = mapped_column(
        String(12), default=Priority.MEDIUM.value, index=True, nullable=False
    )
    action_route: Mapped[str | None] = mapped_column(String(160))

    # Idempotency key — stable within a regeneration window (see collectors).
    dedup_key: Mapped[str] = mapped_column(String(200), index=True, nullable=False)

    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    dismissed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )

    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )

    deliveries: Mapped[list[NotificationDeliveryLog]] = relationship(
        back_populates="notification",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="NotificationDeliveryLog.created_at",
    )


class DeviceToken(UUIDMixin, TimestampMixin, Base):
    """A farmer's push (FCM) device token (Phase 3 — real push delivery).

    Unique per token; a token is deactivated (``is_active=False``) rather than
    deleted so delivery history stays coherent. ``platform`` is ios|android.
    """

    __tablename__ = "device_tokens"
    __table_args__ = (
        UniqueConstraint("token", name="uq_device_tokens_token"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    token: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(10), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )


class NotificationPreferences(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_notification_preferences_user"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )

    # Per-module opt-outs (default on — farmers opt out, never in).
    weather_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    disease_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    calendar_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    growth_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    market_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    scheme_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    produce_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    system_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Channel opt-outs. in_app is the only channel actually implemented today
    # (push/sms/whatsapp/email are reserved for future providers, gated off
    # unless a real provider like FCM is configured — see
    # NotificationService._channels_for); it defaults to on but a farmer can
    # opt out, which stops notifications from being generated for them at all
    # (NotificationService._passes_preferences).
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sms_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    whatsapp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    voice_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Minimum severity gate (info | warning | critical).
    min_severity: Mapped[str] = mapped_column(
        String(12), default=Severity.INFO.value, nullable=False
    )
    language: Mapped[str] = mapped_column(
        String(8), default=DEFAULT_LANGUAGE, nullable=False
    )


class NotificationDeliveryLog(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "notification_delivery_log"

    notification_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("notifications.id"), index=True, nullable=False
    )
    channel: Mapped[str] = mapped_column(String(12), nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False)
    detail: Mapped[str | None] = mapped_column(String(255))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    notification: Mapped[Notification] = relationship(back_populates="deliveries")


class NotificationTemplate(UUIDMixin, TimestampMixin, Base):
    """The rule table materialized in the DB (seeded from ``constants.RULES``)."""

    __tablename__ = "notification_templates"
    __table_args__ = (
        UniqueConstraint(
            "module", "event_type", name="uq_notification_templates_event"
        ),
    )

    module: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title_key: Mapped[str] = mapped_column(String(120), nullable=False)
    message_key: Mapped[str] = mapped_column(String(120), nullable=False)
    severity: Mapped[str] = mapped_column(String(12), nullable=False)
    priority: Mapped[str] = mapped_column(String(12), nullable=False)
    expires_after_hours: Mapped[int | None] = mapped_column(Integer)
    action_route: Mapped[str | None] = mapped_column(String(160))


class FutureNotificationQueue(UUIDMixin, TimestampMixin, Base):
    """A scheduled notification not yet due — promoted into ``notifications``
    by the engine once ``scheduled_for`` passes."""

    __tablename__ = "future_notification_queue"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "dedup_key", name="uq_future_notifications_user_dedup"
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True
    )
    module: Mapped[str] = mapped_column(String(20), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title_key: Mapped[str] = mapped_column(String(120), nullable=False)
    message_key: Mapped[str] = mapped_column(String(120), nullable=False)
    payload_json: Mapped[dict | None] = mapped_column(JSON)
    severity: Mapped[str] = mapped_column(String(12), nullable=False)
    priority: Mapped[str] = mapped_column(String(12), nullable=False)
    action_route: Mapped[str | None] = mapped_column(String(160))
    dedup_key: Mapped[str] = mapped_column(String(200), index=True, nullable=False)

    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
