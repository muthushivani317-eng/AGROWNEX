"""nutrient deficiency tables

Revision ID: 0015_nutrient_tables
Revises: 0014_satellite_tables
Create Date: 2026-07-12
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015_nutrient_tables"
down_revision: str | None = "0014_satellite_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    now = sa.func.now()

    op.create_table(
        "nutrient_reports",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=False),
        sa.Column("crop", sa.String(80), nullable=True),
        sa.Column("image_url", sa.String(512), nullable=False),
        sa.Column("thumbnail_url", sa.String(512), nullable=True),
        sa.Column("capture_method", sa.String(20), nullable=False, server_default="gallery"),
        sa.Column("capture_date", sa.Date(), nullable=True),
        sa.Column("provider", sa.String(24), nullable=False),
        sa.Column("model_used", sa.String(60), nullable=True),
        sa.Column("status", sa.String(12), nullable=False, server_default="analyzed"),
        sa.Column("language", sa.String(5), nullable=False, server_default="ta"),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("weather_snapshot", sa.JSON(), nullable=True),
        sa.Column("raw_response", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("idx_nutrient_reports_user", "nutrient_reports", ["user_id"])
    op.create_index("idx_nutrient_reports_farm", "nutrient_reports", ["farm_id"])
    op.create_index("idx_nutrient_reports_crop", "nutrient_reports", ["crop"])
    op.create_index("idx_nutrient_reports_status", "nutrient_reports", ["status"])
    op.create_index("idx_nutrient_reports_capture", "nutrient_reports", ["capture_date"])

    op.create_table(
        "nutrient_analysis",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("report_id", UUID, sa.ForeignKey("nutrient_reports.id"), nullable=False),
        sa.Column("primary_deficiency", sa.String(20), nullable=True),
        sa.Column("secondary_deficiency", sa.String(20), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("severity", sa.String(12), nullable=False),
        sa.Column("affected_area", sa.String(16), nullable=True),
        sa.Column("soil_reference", sa.JSON(), nullable=True),
        sa.Column("satellite_reference", sa.JSON(), nullable=True),
        sa.Column("weather_reference", sa.JSON(), nullable=True),
        sa.Column("disease_conflict", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("needs_test", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("needs_expert", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("explanation_tamil", sa.Text(), nullable=True),
        sa.Column("explanation_english", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index("idx_nutrient_analysis_report", "nutrient_analysis", ["report_id"])

    op.create_table(
        "nutrient_symptoms",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("report_id", UUID, sa.ForeignKey("nutrient_reports.id"), nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("label", sa.String(160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index("idx_nutrient_symptoms_report", "nutrient_symptoms", ["report_id"])

    op.create_table(
        "nutrient_recommendations",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=False),
        sa.Column("report_id", UUID, sa.ForeignKey("nutrient_reports.id"), nullable=True),
        sa.Column("category", sa.String(16), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("nutrient", sa.String(20), nullable=True),
        sa.Column("severity", sa.String(12), nullable=False),
        sa.Column("priority", sa.String(12), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index("idx_nutrient_recs_user", "nutrient_recommendations", ["user_id"])
    op.create_index("idx_nutrient_recs_farm", "nutrient_recommendations", ["farm_id"])
    op.create_index("idx_nutrient_recs_report", "nutrient_recommendations", ["report_id"])

    op.create_table(
        "nutrient_history",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=False),
        sa.Column("report_id", UUID, sa.ForeignKey("nutrient_reports.id"), nullable=True),
        sa.Column("crop", sa.String(80), nullable=True),
        sa.Column("primary_deficiency", sa.String(20), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("severity", sa.String(12), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index("idx_nutrient_history_user", "nutrient_history", ["user_id"])
    op.create_index("idx_nutrient_history_farm", "nutrient_history", ["farm_id"])
    op.create_index("idx_nutrient_history_report", "nutrient_history", ["report_id"])


def downgrade() -> None:
    op.drop_table("nutrient_history")
    op.drop_table("nutrient_recommendations")
    op.drop_table("nutrient_symptoms")
    op.drop_table("nutrient_analysis")
    op.drop_table("nutrient_reports")
