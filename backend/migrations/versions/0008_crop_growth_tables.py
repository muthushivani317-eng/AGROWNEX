"""crop growth monitor tables

Revision ID: 0008_crop_growth_tables
Revises: 0007_market_tables
Create Date: 2026-07-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_crop_growth_tables"
down_revision: str | None = "0007_market_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    now = sa.func.now()

    op.create_table(
        "crop_growth_sessions",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=False),
        sa.Column("crop", sa.String(80), nullable=True),
        sa.Column("variety", sa.String(80), nullable=True),
        sa.Column("title", sa.String(160), nullable=True),
        sa.Column("sowing_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(12), nullable=False, server_default="active"),
        sa.Column(
            "current_growth_stage",
            sa.String(20),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column("latest_health_score", sa.Integer(), nullable=True),
        sa.Column("latest_risk_level", sa.String(12), nullable=True),
        sa.Column("image_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("idx_growth_sessions_user", "crop_growth_sessions", ["user_id"])
    op.create_index("idx_growth_sessions_farm", "crop_growth_sessions", ["farm_id"])
    op.create_index("idx_growth_sessions_crop", "crop_growth_sessions", ["crop"])
    op.create_index("idx_growth_sessions_status", "crop_growth_sessions", ["status"])

    op.create_table(
        "crop_growth_images",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "session_id",
            UUID,
            sa.ForeignKey("crop_growth_sessions.id"),
            nullable=False,
        ),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=True),
        sa.Column("image_url", sa.String(512), nullable=False),
        sa.Column("thumbnail_url", sa.String(512), nullable=True),
        sa.Column("capture_method", sa.String(20), nullable=True, server_default="gallery"),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("week_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("weather_snapshot", sa.JSON(), nullable=True),
        sa.Column("image_quality", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("idx_growth_images_session", "crop_growth_images", ["session_id"])
    op.create_index("idx_growth_images_user", "crop_growth_images", ["user_id"])
    op.create_index("idx_growth_images_farm", "crop_growth_images", ["farm_id"])

    op.create_table(
        "crop_growth_analysis",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "image_id",
            UUID,
            sa.ForeignKey("crop_growth_images.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "session_id",
            UUID,
            sa.ForeignKey("crop_growth_sessions.id"),
            nullable=False,
        ),
        sa.Column("growth_stage", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("plant_vigor", sa.String(12), nullable=False, server_default="unknown"),
        sa.Column("health_score", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=True),
        sa.Column("leaf_color_observations", sa.JSON(), nullable=True),
        sa.Column("visible_abnormalities", sa.JSON(), nullable=True),
        sa.Column("changes_from_previous", sa.JSON(), nullable=True),
        sa.Column("recommendations", sa.JSON(), nullable=True),
        sa.Column("disease_result", sa.JSON(), nullable=True),
        sa.Column("nutrient_result", sa.JSON(), nullable=True),
        sa.Column("needs_expert_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("growth_summary_tamil", sa.Text(), nullable=True),
        sa.Column("growth_summary_english", sa.Text(), nullable=True),
        sa.Column("model_used", sa.String(60), nullable=True),
        sa.Column("raw_response", sa.JSON(), nullable=True),
        sa.Column("language", sa.String(5), nullable=False, server_default="ta"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index("idx_growth_analysis_image", "crop_growth_analysis", ["image_id"])
    op.create_index(
        "idx_growth_analysis_session", "crop_growth_analysis", ["session_id"]
    )

    op.create_table(
        "crop_growth_timelines",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "session_id",
            UUID,
            sa.ForeignKey("crop_growth_sessions.id"),
            nullable=False,
        ),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "image_id", UUID, sa.ForeignKey("crop_growth_images.id"), nullable=False
        ),
        sa.Column("week_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("growth_stage", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("health_score", sa.Integer(), nullable=True),
        sa.Column("health_delta", sa.Integer(), nullable=True),
        sa.Column("risk_level", sa.String(12), nullable=False, server_default="low"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index(
        "idx_growth_timelines_session", "crop_growth_timelines", ["session_id"]
    )
    op.create_index("idx_growth_timelines_user", "crop_growth_timelines", ["user_id"])


def downgrade() -> None:
    op.drop_table("crop_growth_timelines")
    op.drop_table("crop_growth_analysis")
    op.drop_table("crop_growth_images")
    op.drop_table("crop_growth_sessions")
