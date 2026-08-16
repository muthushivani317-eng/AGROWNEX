"""Add evidence-bound waterlogging assessments.

Revision ID: 0b9a62c410df
Revises: f07ad31c62b1
"""

import sqlalchemy as sa
from alembic import op

revision = "0b9a62c410df"
down_revision = "f07ad31c62b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "waterlogging_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("farm_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True)),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(40)),
        sa.Column("coverage_pct", sa.Float()),
        sa.Column("freshness", sa.String(12), nullable=False),
        sa.Column("explanation", sa.String(500), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_waterlogging_assessments_user_id", "waterlogging_assessments", ["user_id"])
    op.create_index("ix_waterlogging_assessments_farm_id", "waterlogging_assessments", ["farm_id"])
    op.create_index(
        "ix_waterlogging_assessments_decision", "waterlogging_assessments", ["decision"]
    )


def downgrade() -> None:
    op.drop_table("waterlogging_assessments")
