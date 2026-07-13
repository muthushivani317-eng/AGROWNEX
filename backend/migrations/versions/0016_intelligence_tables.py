"""crop intelligence engine tables

Revision ID: 0016_intelligence_tables
Revises: 0015_nutrient_tables
Create Date: 2026-07-12
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016_intelligence_tables"
down_revision: str | None = "0015_nutrient_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    now = sa.func.now()

    op.create_table(
        "crop_intelligence_reports",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=False),
        sa.Column("crop", sa.String(80), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("overall_health_score", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("overall_risk", sa.String(12), nullable=False, server_default="low"),
        sa.Column("sources_used", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("idx_ci_reports_user", "crop_intelligence_reports", ["user_id"])
    op.create_index("idx_ci_reports_farm", "crop_intelligence_reports", ["farm_id"])
    op.create_index("idx_ci_reports_generated", "crop_intelligence_reports", ["generated_at"])

    op.create_table(
        "crop_health_scores",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("report_id", UUID, sa.ForeignKey("crop_intelligence_reports.id"), nullable=False),
        sa.Column("overall_health_score", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("disease_score", sa.Integer(), nullable=True),
        sa.Column("nutrient_score", sa.Integer(), nullable=True),
        sa.Column("soil_score", sa.Integer(), nullable=True),
        sa.Column("satellite_score", sa.Integer(), nullable=True),
        sa.Column("weather_score", sa.Integer(), nullable=True),
        sa.Column("growth_score", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index("idx_ci_health_report", "crop_health_scores", ["report_id"])

    op.create_table(
        "crop_risk_scores",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("report_id", UUID, sa.ForeignKey("crop_intelligence_reports.id"), nullable=False),
        sa.Column("overall_risk", sa.String(12), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=True),
        sa.Column("priority_issues", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index("idx_ci_risk_report", "crop_risk_scores", ["report_id"])

    op.create_table(
        "crop_recommendations",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("report_id", UUID, sa.ForeignKey("crop_intelligence_reports.id"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("priority", sa.String(12), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("modules", sa.JSON(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index("idx_ci_recs_report", "crop_recommendations", ["report_id"])
    op.create_index("idx_ci_recs_user", "crop_recommendations", ["user_id"])
    op.create_index("idx_ci_recs_farm", "crop_recommendations", ["farm_id"])

    op.create_table(
        "crop_decision_history",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=False),
        sa.Column("report_id", UUID, sa.ForeignKey("crop_intelligence_reports.id"), nullable=True),
        sa.Column("overall_health_score", sa.Integer(), nullable=True),
        sa.Column("overall_risk", sa.String(12), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index("idx_ci_history_user", "crop_decision_history", ["user_id"])
    op.create_index("idx_ci_history_farm", "crop_decision_history", ["farm_id"])
    op.create_index("idx_ci_history_report", "crop_decision_history", ["report_id"])


def downgrade() -> None:
    op.drop_table("crop_decision_history")
    op.drop_table("crop_recommendations")
    op.drop_table("crop_risk_scores")
    op.drop_table("crop_health_scores")
    op.drop_table("crop_intelligence_reports")
