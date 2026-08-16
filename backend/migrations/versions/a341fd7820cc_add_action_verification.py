"""Add workflow-only farmer action verification.

Revision ID: a341fd7820cc
Revises: 9b6e31fa2870
"""

import sqlalchemy as sa
from alembic import op

revision = "a341fd7820cc"
down_revision = "9b6e31fa2870"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "action_workflows",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", sa.Uuid(), sa.ForeignKey("farms.id"), nullable=False),
        sa.Column("crop_cycle_id", sa.String(80)),
        sa.Column("source_module", sa.String(40), nullable=False),
        sa.Column("source_record_id", sa.String(100), nullable=False),
        sa.Column("source_version", sa.String(80), nullable=False),
        sa.Column("action_code", sa.String(120), nullable=False),
        sa.Column("source_verified", sa.Boolean(), nullable=False),
        sa.Column("farmer_created", sa.Boolean(), nullable=False),
        sa.Column("suggestion_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("outcome_status", sa.String(40), nullable=False),
        sa.Column("verification_scope", sa.String(40), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("pending_sync", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "action_audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("action_id", sa.Uuid(), sa.ForeignKey("action_workflows.id")),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("actor_type", sa.String(20), nullable=False),
        sa.Column("event", sa.String(30), nullable=False),
        sa.Column("prior_status", sa.String(40)),
        sa.Column("new_status", sa.String(40), nullable=False),
        sa.Column("request_id", sa.String(100), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("source_version", sa.String(80), nullable=False),
        sa.Column("note", sa.String(500)),
        sa.Column("reason", sa.String(500)),
        sa.Column("evidence_hash", sa.String(64)),
        sa.Column("evidence_storage_ref", sa.String(512)),
        sa.Column("evidence_mime_type", sa.String(40)),
        sa.Column("evidence_captured_at", sa.DateTime(timezone=True)),
        sa.Column("retention_consent", sa.Boolean(), nullable=False),
        sa.Column("supersedes_event_id", sa.Uuid()),
        sa.Column("farmer_reported", sa.Boolean(), nullable=False),
        sa.Column("expert_reviewed", sa.Boolean(), nullable=False),
        sa.Column("event_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("actor_user_id", "idempotency_key", name="uq_action_actor_key"),
    )


def downgrade() -> None:
    op.drop_table("action_audit_events")
    op.drop_table("action_workflows")
