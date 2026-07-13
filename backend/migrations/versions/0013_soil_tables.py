"""soil intelligence tables

Revision ID: 0013_soil_tables
Revises: 0012_expert_tables
Create Date: 2026-07-12
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_soil_tables"
down_revision: str | None = "0012_expert_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    now = sa.func.now()

    op.create_table(
        "soil_profiles",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=False),
        sa.Column("soil_type", sa.String(60), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("ph", sa.Float(), nullable=True),
        sa.Column("organic_carbon", sa.Float(), nullable=True),
        sa.Column("nitrogen", sa.Float(), nullable=True),
        sa.Column("phosphorus", sa.Float(), nullable=True),
        sa.Column("potassium", sa.Float(), nullable=True),
        sa.Column("micronutrients", sa.JSON(), nullable=True),
        sa.Column("ec_salinity", sa.Float(), nullable=True),
        sa.Column("water_holding_capacity", sa.Float(), nullable=True),
        sa.Column("drainage", sa.String(20), nullable=True),
        sa.Column("source", sa.String(24), nullable=False, server_default="self"),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_test_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("farm_id", name="uq_soil_profiles_farm"),
    )
    op.create_index("idx_soil_profiles_user", "soil_profiles", ["user_id"])
    op.create_index("idx_soil_profiles_farm", "soil_profiles", ["farm_id"])

    op.create_table(
        "soil_reports",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=False),
        sa.Column("source", sa.String(24), nullable=False, server_default="self"),
        sa.Column("report_url", sa.String(512), nullable=True),
        sa.Column("thumbnail_url", sa.String(512), nullable=True),
        sa.Column("mime_type", sa.String(80), nullable=True),
        sa.Column("lab_name", sa.String(160), nullable=True),
        sa.Column("test_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(12), nullable=False, server_default="submitted"),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("idx_soil_reports_user", "soil_reports", ["user_id"])
    op.create_index("idx_soil_reports_farm", "soil_reports", ["farm_id"])
    op.create_index("idx_soil_reports_source", "soil_reports", ["source"])
    op.create_index("idx_soil_reports_status", "soil_reports", ["status"])
    op.create_index("idx_soil_reports_test_date", "soil_reports", ["test_date"])

    op.create_table(
        "soil_test_results",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("report_id", UUID, sa.ForeignKey("soil_reports.id"), nullable=False),
        sa.Column("ph", sa.Float(), nullable=True),
        sa.Column("organic_carbon", sa.Float(), nullable=True),
        sa.Column("nitrogen", sa.Float(), nullable=True),
        sa.Column("phosphorus", sa.Float(), nullable=True),
        sa.Column("potassium", sa.Float(), nullable=True),
        sa.Column("sulphur", sa.Float(), nullable=True),
        sa.Column("ec_salinity", sa.Float(), nullable=True),
        sa.Column("water_holding_capacity", sa.Float(), nullable=True),
        sa.Column("drainage", sa.String(20), nullable=True),
        sa.Column("micronutrients", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index("idx_soil_test_results_report", "soil_test_results", ["report_id"])

    op.create_table(
        "soil_recommendations",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=False),
        sa.Column("report_id", UUID, sa.ForeignKey("soil_reports.id"), nullable=True),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("parameter", sa.String(30), nullable=True),
        sa.Column("rating", sa.String(20), nullable=True),
        sa.Column("severity", sa.String(12), nullable=False),
        sa.Column("priority", sa.String(12), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(12), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index("idx_soil_recommendations_user", "soil_recommendations", ["user_id"])
    op.create_index("idx_soil_recommendations_farm", "soil_recommendations", ["farm_id"])
    op.create_index(
        "idx_soil_recommendations_report", "soil_recommendations", ["report_id"]
    )

    op.create_table(
        "soil_history",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=False),
        sa.Column("report_id", UUID, sa.ForeignKey("soil_reports.id"), nullable=True),
        sa.Column("test_date", sa.Date(), nullable=True),
        sa.Column("ph", sa.Float(), nullable=True),
        sa.Column("organic_carbon", sa.Float(), nullable=True),
        sa.Column("nitrogen", sa.Float(), nullable=True),
        sa.Column("phosphorus", sa.Float(), nullable=True),
        sa.Column("potassium", sa.Float(), nullable=True),
        sa.Column("source", sa.String(24), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index("idx_soil_history_user", "soil_history", ["user_id"])
    op.create_index("idx_soil_history_farm", "soil_history", ["farm_id"])
    op.create_index("idx_soil_history_report", "soil_history", ["report_id"])
    op.create_index("idx_soil_history_test_date", "soil_history", ["test_date"])


def downgrade() -> None:
    op.drop_table("soil_history")
    op.drop_table("soil_recommendations")
    op.drop_table("soil_test_results")
    op.drop_table("soil_reports")
    op.drop_table("soil_profiles")
