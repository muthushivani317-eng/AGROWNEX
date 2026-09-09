"""add trusted organic weather provenance

Revision ID: e5a9c72f3d01
Revises: d4f8b61e2c90
"""

import sqlalchemy as sa
from alembic import op

revision = "e5a9c72f3d01"
down_revision = "d4f8b61e2c90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organic_weather_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("farm_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("provider_fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_organic_weather_snapshots_user_id", "organic_weather_snapshots", ["user_id"]
    )
    op.create_index(
        "ix_organic_weather_snapshots_farm_id", "organic_weather_snapshots", ["farm_id"]
    )
    op.create_table(
        "organic_action_reschedules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("farm_id", sa.Uuid(), nullable=False),
        sa.Column("action_workflow_id", sa.Uuid(), nullable=False),
        sa.Column("weather_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("signal_code", sa.String(50), nullable=False),
        sa.Column("prior_due_at", sa.DateTime(timezone=True)),
        sa.Column("rescheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"]),
        sa.ForeignKeyConstraint(["action_workflow_id"], ["action_workflows.id"]),
        sa.ForeignKeyConstraint(["weather_snapshot_id"], ["organic_weather_snapshots.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_organic_reschedule_idempotency"),
    )
    op.create_index(
        "ix_organic_action_reschedules_user_id", "organic_action_reschedules", ["user_id"]
    )
    op.create_index(
        "ix_organic_action_reschedules_farm_id", "organic_action_reschedules", ["farm_id"]
    )
    op.create_index(
        "ix_organic_action_reschedules_action_workflow_id",
        "organic_action_reschedules",
        ["action_workflow_id"],
    )
    op.create_table(
        "organic_notification_intents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("farm_id", sa.Uuid(), nullable=False),
        sa.Column("reschedule_id", sa.Uuid(), nullable=False),
        sa.Column("dedup_key", sa.String(200), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"]),
        sa.ForeignKeyConstraint(["reschedule_id"], ["organic_action_reschedules.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "dedup_key", name="uq_organic_notification_intent"),
    )
    op.create_index(
        "ix_organic_notification_intents_user_id", "organic_notification_intents", ["user_id"]
    )
    op.create_index(
        "ix_organic_notification_intents_farm_id", "organic_notification_intents", ["farm_id"]
    )


def downgrade() -> None:
    op.drop_table("organic_notification_intents")
    op.drop_table("organic_action_reschedules")
    op.drop_table("organic_weather_snapshots")
