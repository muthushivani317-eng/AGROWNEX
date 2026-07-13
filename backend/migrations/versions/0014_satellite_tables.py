"""satellite intelligence tables

Revision ID: 0014_satellite_tables
Revises: 0013_soil_tables
Create Date: 2026-07-12
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014_satellite_tables"
down_revision: str | None = "0013_soil_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    now = sa.func.now()

    op.create_table(
        "satellite_sessions",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=False),
        sa.Column("provider", sa.String(24), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="pending"),
        sa.Column("unavailable_reason", sa.String(20), nullable=False, server_default="none"),
        sa.Column("is_sample", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("capture_date", sa.Date(), nullable=True),
        sa.Column("cloud_cover", sa.Float(), nullable=True),
        sa.Column("resolution_m", sa.Float(), nullable=True),
        sa.Column("ndvi", sa.Float(), nullable=True),
        sa.Column("ndre", sa.Float(), nullable=True),
        sa.Column("evi", sa.Float(), nullable=True),
        sa.Column("ndmi", sa.Float(), nullable=True),
        sa.Column("vegetation_health", sa.String(12), nullable=True),
        sa.Column("stress_level", sa.String(12), nullable=True),
        sa.Column("moisture_status", sa.String(12), nullable=True),
        sa.Column("trend", sa.String(12), nullable=True),
        sa.Column("ndvi_delta", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("idx_satellite_sessions_user", "satellite_sessions", ["user_id"])
    op.create_index("idx_satellite_sessions_farm", "satellite_sessions", ["farm_id"])
    op.create_index("idx_satellite_sessions_status", "satellite_sessions", ["status"])
    op.create_index("idx_satellite_sessions_capture", "satellite_sessions", ["capture_date"])

    op.create_table(
        "satellite_images",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", UUID, sa.ForeignKey("satellite_sessions.id"), nullable=False),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=False),
        sa.Column("band", sa.String(16), nullable=False),
        sa.Column("image_url", sa.String(512), nullable=False),
        sa.Column("thumbnail_url", sa.String(512), nullable=True),
        sa.Column("mime_type", sa.String(80), nullable=True),
        sa.Column("resolution_m", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index("idx_satellite_images_session", "satellite_images", ["session_id"])
    op.create_index("idx_satellite_images_farm", "satellite_images", ["farm_id"])

    op.create_table(
        "satellite_indices",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", UUID, sa.ForeignKey("satellite_sessions.id"), nullable=False),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=False),
        sa.Column("index_name", sa.String(8), nullable=False),
        sa.Column("mean", sa.Float(), nullable=True),
        sa.Column("minimum", sa.Float(), nullable=True),
        sa.Column("maximum", sa.Float(), nullable=True),
        sa.Column("std", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index("idx_satellite_indices_session", "satellite_indices", ["session_id"])

    op.create_table(
        "satellite_alerts",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("session_id", UUID, sa.ForeignKey("satellite_sessions.id"), nullable=False),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("category", sa.String(16), nullable=False),
        sa.Column("severity", sa.String(12), nullable=False),
        sa.Column("priority", sa.String(12), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index("idx_satellite_alerts_user", "satellite_alerts", ["user_id"])
    op.create_index("idx_satellite_alerts_session", "satellite_alerts", ["session_id"])
    op.create_index("idx_satellite_alerts_farm", "satellite_alerts", ["farm_id"])

    op.create_table(
        "satellite_history",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=False),
        sa.Column("session_id", UUID, sa.ForeignKey("satellite_sessions.id"), nullable=True),
        sa.Column("capture_date", sa.Date(), nullable=True),
        sa.Column("ndvi", sa.Float(), nullable=True),
        sa.Column("ndre", sa.Float(), nullable=True),
        sa.Column("evi", sa.Float(), nullable=True),
        sa.Column("ndmi", sa.Float(), nullable=True),
        sa.Column("vegetation_health", sa.String(12), nullable=True),
        sa.Column("stress_level", sa.String(12), nullable=True),
        sa.Column("moisture_status", sa.String(12), nullable=True),
        sa.Column("source", sa.String(24), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index("idx_satellite_history_user", "satellite_history", ["user_id"])
    op.create_index("idx_satellite_history_farm", "satellite_history", ["farm_id"])
    op.create_index("idx_satellite_history_session", "satellite_history", ["session_id"])
    op.create_index("idx_satellite_history_capture", "satellite_history", ["capture_date"])


def downgrade() -> None:
    op.drop_table("satellite_history")
    op.drop_table("satellite_alerts")
    op.drop_table("satellite_indices")
    op.drop_table("satellite_images")
    op.drop_table("satellite_sessions")
