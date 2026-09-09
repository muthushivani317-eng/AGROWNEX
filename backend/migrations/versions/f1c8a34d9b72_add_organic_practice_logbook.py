"""add farmer-owned organic practice logbook

Revision ID: f1c8a34d9b72
Revises: e4b7c2d91a60
"""

import sqlalchemy as sa
from alembic import op

from app.shared.base_model import GUID

revision = "f1c8a34d9b72"
down_revision = "e4b7c2d91a60"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "organic_practice_log_entries",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", GUID(), sa.ForeignKey("farms.id"), nullable=False),
        sa.Column("crop_cycle_id", sa.String(80)),
        sa.Column("action_workflow_id", GUID(), sa.ForeignKey("action_workflows.id")),
        sa.Column("daily_task_id", GUID(), sa.ForeignKey("daily_tasks.id")),
        sa.Column("practice_type", sa.String(50), nullable=False),
        sa.Column("practice_code", sa.String(120), nullable=False),
        sa.Column("input_reference", sa.String(120)),
        sa.Column("quantity", sa.Float()),
        sa.Column("quantity_unit", sa.String(30)),
        sa.Column("treated_area_hectares", sa.Float()),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("outcome_status", sa.String(40), nullable=False, server_default="not_reported"),
        sa.Column("source_feature", sa.String(40), nullable=False),
        sa.Column("source_record_id", sa.String(100), nullable=False),
        sa.Column("source_version", sa.String(80), nullable=False),
        sa.Column("source_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "verification_status", sa.String(40), nullable=False, server_default="farmer_reported"
        ),
        sa.Column("expert_reviewed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        *_timestamps(),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint(
            "user_id", "idempotency_key", name="uq_organic_log_user_idempotency"
        ),
    )
    op.create_index(
        "ix_organic_practice_log_entries_user_id", "organic_practice_log_entries", ["user_id"]
    )
    op.create_index(
        "ix_organic_practice_log_entries_farm_id", "organic_practice_log_entries", ["farm_id"]
    )
    op.create_index(
        "ix_organic_practice_log_entries_action_workflow_id",
        "organic_practice_log_entries",
        ["action_workflow_id"],
    )
    op.create_index(
        "ix_organic_practice_log_entries_daily_task_id",
        "organic_practice_log_entries",
        ["daily_task_id"],
    )
    op.create_index(
        "ix_organic_practice_log_entries_practice_type",
        "organic_practice_log_entries",
        ["practice_type"],
    )
    op.create_index(
        "ix_organic_log_farm_occurred",
        "organic_practice_log_entries",
        ["farm_id", "occurred_at"],
    )

    op.create_table(
        "organic_practice_evidence",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column(
            "entry_id",
            GUID(),
            sa.ForeignKey("organic_practice_log_entries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("evidence_type", sa.String(20), nullable=False),
        sa.Column("storage_ref", sa.String(512), nullable=False),
        sa.Column("content_hash", sa.String(64)),
        sa.Column("mime_type", sa.String(80)),
        sa.Column("captured_at", sa.DateTime(timezone=True)),
        sa.Column("retention_consent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("farmer_reported", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("expert_reviewed", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_timestamps(),
    )
    op.create_index(
        "ix_organic_practice_evidence_entry_id", "organic_practice_evidence", ["entry_id"]
    )


def downgrade() -> None:
    op.drop_table("organic_practice_evidence")
    op.drop_table("organic_practice_log_entries")
