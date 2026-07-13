"""notifications & smart alerts tables (the event center)

Revision ID: 0011_notification_tables
Revises: 0010_produce_tables
Create Date: 2026-07-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_notification_tables"
down_revision: str | None = "0010_produce_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    now = sa.func.now()

    op.create_table(
        "notifications",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=True),
        sa.Column("module", sa.String(20), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("title_key", sa.String(120), nullable=False),
        sa.Column("message_key", sa.String(120), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("severity", sa.String(12), nullable=False, server_default="info"),
        sa.Column("priority", sa.String(12), nullable=False, server_default="medium"),
        sa.Column("action_route", sa.String(160), nullable=True),
        sa.Column("dedup_key", sa.String(200), nullable=False),
        sa.Column("read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("dismissed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("user_id", "dedup_key", name="uq_notifications_user_dedup"),
    )
    op.create_index("idx_notifications_user", "notifications", ["user_id"])
    op.create_index("idx_notifications_farm", "notifications", ["farm_id"])
    op.create_index("idx_notifications_module", "notifications", ["module"])
    op.create_index("idx_notifications_priority", "notifications", ["priority"])
    op.create_index("idx_notifications_dedup", "notifications", ["dedup_key"])
    op.create_index("idx_notifications_read", "notifications", ["read"])
    op.create_index("idx_notifications_dismissed", "notifications", ["dismissed"])
    op.create_index("idx_notifications_expires", "notifications", ["expires_at"])

    op.create_table(
        "notification_preferences",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("weather_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("disease_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("calendar_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("growth_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("market_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("scheme_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("produce_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("ai_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("system_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("in_app_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("push_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sms_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("whatsapp_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("voice_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("min_severity", sa.String(12), nullable=False, server_default="info"),
        sa.Column("language", sa.String(8), nullable=False, server_default="ta"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.UniqueConstraint("user_id", name="uq_notification_preferences_user"),
    )
    op.create_index(
        "idx_notification_preferences_user", "notification_preferences", ["user_id"]
    )

    op.create_table(
        "notification_delivery_log",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "notification_id", UUID, sa.ForeignKey("notifications.id"), nullable=False
        ),
        sa.Column("channel", sa.String(12), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("detail", sa.String(255), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index(
        "idx_notification_delivery_notification",
        "notification_delivery_log",
        ["notification_id"],
    )

    op.create_table(
        "notification_templates",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("module", sa.String(20), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("title_key", sa.String(120), nullable=False),
        sa.Column("message_key", sa.String(120), nullable=False),
        sa.Column("severity", sa.String(12), nullable=False),
        sa.Column("priority", sa.String(12), nullable=False),
        sa.Column("expires_after_hours", sa.Integer(), nullable=True),
        sa.Column("action_route", sa.String(160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.UniqueConstraint(
            "module", "event_type", name="uq_notification_templates_event"
        ),
    )
    op.create_index(
        "idx_notification_templates_module", "notification_templates", ["module"]
    )

    op.create_table(
        "future_notification_queue",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=True),
        sa.Column("module", sa.String(20), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("title_key", sa.String(120), nullable=False),
        sa.Column("message_key", sa.String(120), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("severity", sa.String(12), nullable=False),
        sa.Column("priority", sa.String(12), nullable=False),
        sa.Column("action_route", sa.String(160), nullable=True),
        sa.Column("dedup_key", sa.String(200), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.UniqueConstraint(
            "user_id", "dedup_key", name="uq_future_notifications_user_dedup"
        ),
    )
    op.create_index(
        "idx_future_notifications_user", "future_notification_queue", ["user_id"]
    )
    op.create_index(
        "idx_future_notifications_scheduled",
        "future_notification_queue",
        ["scheduled_for"],
    )
    op.create_index(
        "idx_future_notifications_processed",
        "future_notification_queue",
        ["processed"],
    )
    op.create_index(
        "idx_future_notifications_dedup", "future_notification_queue", ["dedup_key"]
    )


def downgrade() -> None:
    op.drop_table("future_notification_queue")
    op.drop_table("notification_templates")
    op.drop_table("notification_delivery_log")
    op.drop_table("notification_preferences")
    op.drop_table("notifications")
