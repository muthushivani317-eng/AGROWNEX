"""Add crop-stage state and immutable transition history.

Revision ID: 7d2a349cc840
Revises: 4d12a6b7c903, 8df904e2c11a

Note: 0b9a62c410df is the common ancestor of both 4d12a6b7c903 and
8df904e2c11a (each declares it as their own down_revision), not a
third independent head. Listing it again here as a down_revision
caused alembic to try to retire it a second time during `upgrade
head`, once when 4d12a6b7c903/8df904e2c11a ran and again here,
raising `KeyError: '0b9a62c410df'` from `_delete_version` (found
while deploying a fresh database for the 2026-08 pre-release --
0b9a62c410df was already removed from the live `heads` set by the
time this merge step ran).
"""

import sqlalchemy as sa
from alembic import op

revision = "7d2a349cc840"
down_revision = ("4d12a6b7c903", "8df904e2c11a")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crop_stage_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("farm_id", sa.Uuid(), nullable=False),
        sa.Column("crop_cycle_id", sa.String(80), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("suggested_stage", sa.String(20)),
        sa.Column("confirmed_stage", sa.String(20)),
        sa.Column("registry_version", sa.String(80)),
        sa.Column("calculation_version", sa.String(40), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("pending_sync", sa.Boolean(), nullable=False),
        sa.Column("evidence_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "farm_id", "crop_cycle_id", name="uq_crop_stage_cycle"),
    )
    op.create_table(
        "crop_stage_transitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("state_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("event", sa.String(20), nullable=False),
        sa.Column("prior_state", sa.String(32)),
        sa.Column("next_state", sa.String(32), nullable=False),
        sa.Column("prior_stage", sa.String(20)),
        sa.Column("stage", sa.String(20)),
        sa.Column("reason", sa.String(500)),
        sa.Column("photo_reference", sa.String(512)),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("registry_version", sa.String(80)),
        sa.Column("evidence_snapshot", sa.JSON(), nullable=False),
        sa.Column("expert_reviewed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["state_id"], ["crop_stage_states.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_crop_stage_transition_user_key"),
    )
    op.create_index("ix_crop_stage_states_user_id", "crop_stage_states", ["user_id"])
    op.create_index("ix_crop_stage_states_farm_id", "crop_stage_states", ["farm_id"])
    op.create_index("ix_crop_stage_states_crop_cycle_id", "crop_stage_states", ["crop_cycle_id"])
    op.create_index("ix_crop_stage_transitions_state_id", "crop_stage_transitions", ["state_id"])
    op.create_index("ix_crop_stage_transitions_user_id", "crop_stage_transitions", ["user_id"])
    op.create_index(
        "ix_crop_stage_transitions_idempotency_key",
        "crop_stage_transitions",
        ["idempotency_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("crop_stage_transitions")
    op.drop_table("crop_stage_states")
