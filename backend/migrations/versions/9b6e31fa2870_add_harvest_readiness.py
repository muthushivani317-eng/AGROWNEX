"""Add evidence-bound harvest readiness records.

Revision ID: 9b6e31fa2870
Revises: 7d2a349cc840
"""

import sqlalchemy as sa
from alembic import op

revision = "9b6e31fa2870"
down_revision = "7d2a349cc840"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "harvest_readiness_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", sa.Uuid(), sa.ForeignKey("farms.id"), nullable=False),
        sa.Column("crop_cycle_id", sa.String(80), nullable=False),
        sa.Column("state", sa.String(40), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("criteria_version", sa.String(80)),
        sa.Column("criteria_hash", sa.String(64)),
        sa.Column("evidence_snapshot", sa.JSON(), nullable=False),
        sa.Column("pending_sync", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("user_id", "farm_id", "crop_cycle_id", name="uq_harvest_cycle"),
    )
    op.create_table(
        "harvest_readiness_history",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("record_id", sa.Uuid(), sa.ForeignKey("harvest_readiness_records.id")),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event", sa.String(24), nullable=False),
        sa.Column("prior_state", sa.String(40)),
        sa.Column("next_state", sa.String(40), nullable=False),
        sa.Column("note", sa.String(500)),
        sa.Column("photo_reference", sa.String(512)),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("evidence_snapshot", sa.JSON(), nullable=False),
        sa.Column("farmer_confirmed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_harvest_user_key"),
    )


def downgrade() -> None:
    op.drop_table("harvest_readiness_history")
    op.drop_table("harvest_readiness_records")
