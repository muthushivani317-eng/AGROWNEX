"""crop calendar events table

Revision ID: 0006_crop_calendar_events
Revises: 0005_disease_reports
Create Date: 2026-07-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_crop_calendar_events"
down_revision: str | None = "0005_disease_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    now = sa.func.now()
    op.create_table(
        "crop_calendar_events",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=False),
        sa.Column("crop_session_id", UUID, nullable=True),
        sa.Column("code", sa.String(60), nullable=False),
        sa.Column("activity_type", sa.String(40), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("day_offset", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("crop", sa.String(80), nullable=True),
        sa.Column("season", sa.String(20), nullable=True),
        sa.Column("growth_stage", sa.String(20), nullable=False),
        sa.Column("priority", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(10), nullable=False, server_default="pending"),
        sa.Column(
            "weather_dependency", sa.String(20), nullable=False, server_default="none"
        ),
        sa.Column(
            "reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("reminder_hour", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("idx_calendar_events_user", "crop_calendar_events", ["user_id"])
    op.create_index("idx_calendar_events_farm", "crop_calendar_events", ["farm_id"])
    op.create_index("idx_calendar_events_crop", "crop_calendar_events", ["crop"])
    op.create_index("idx_calendar_events_status", "crop_calendar_events", ["status"])
    op.create_index(
        "idx_calendar_events_date", "crop_calendar_events", ["scheduled_date"]
    )


def downgrade() -> None:
    op.drop_table("crop_calendar_events")
