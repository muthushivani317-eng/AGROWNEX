"""Add immutable soil indicator evidence.

Revision ID: 4d12a6b7c903
Revises: 0b9a62c410df
"""

import sqlalchemy as sa
from alembic import op

revision = "4d12a6b7c903"
down_revision = "0b9a62c410df"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "soil_indicator_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("farm_id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid()),
        sa.Column("indicator", sa.String(40), nullable=False),
        sa.Column("numeric_value", sa.Float()),
        sa.Column("text_value", sa.String(80)),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("evidence_type", sa.String(32), nullable=False),
        sa.Column("collection_method", sa.String(80), nullable=False),
        sa.Column("collected_at", sa.Date(), nullable=False),
        sa.Column("source_reference", sa.String(256), nullable=False),
        sa.Column("spatial_coverage", sa.String(40), nullable=False),
        sa.Column("confidence", sa.Integer()),
        sa.Column("uncertainty_low", sa.Float()),
        sa.Column("uncertainty_high", sa.Float()),
        sa.Column("verification_state", sa.String(24), nullable=False),
        sa.Column("report_reference", sa.String(256)),
        sa.Column("provenance", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"]),
        sa.ForeignKeyConstraint(["report_id"], ["soil_reports.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("user_id", "farm_id", "report_id", "indicator", "collected_at"):
        op.create_index(f"ix_soil_indicator_evidence_{column}", "soil_indicator_evidence", [column])


def downgrade() -> None:
    op.drop_table("soil_indicator_evidence")
