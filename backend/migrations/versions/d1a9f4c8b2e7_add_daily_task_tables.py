"""add today's farm task advisory-layer tables

Revision ID: d1a9f4c8b2e7
Revises: b7f5e21c9a40
"""

import sqlalchemy as sa
from alembic import op

from app.shared.base_model import GUID

revision = "d1a9f4c8b2e7"
down_revision = "b7f5e21c9a40"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "daily_signals",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("farm_id", GUID(), sa.ForeignKey("farms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("signal_type", sa.String(64), nullable=False),
        sa.Column("source_module", sa.String(32), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confidence", sa.String(16), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("urgency", sa.String(16), nullable=False),
        sa.Column("evidence_summary", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("evidence_technical", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("evidence_refs", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("policy_flags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("recommended_task_type", sa.String(64), nullable=False),
        sa.Column("dedupe_key", sa.String(256), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="candidate"),
        sa.Column("status_reason", sa.Text(), nullable=True),
        sa.Column("rank_score", sa.Float(), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("dedupe_key", "observed_at", name="uq_daily_signal_dedupe_observed"),
    )
    op.create_index("ix_daily_signals_farm_id", "daily_signals", ["farm_id"])
    op.create_index("ix_daily_signals_user_id", "daily_signals", ["user_id"])
    op.create_index("ix_daily_signals_signal_type", "daily_signals", ["signal_type"])
    op.create_index("ix_daily_signals_status", "daily_signals", ["status"])
    op.create_index("ix_daily_signals_dedupe_key", "daily_signals", ["dedupe_key"])
    op.create_index("ix_daily_signal_farm_status", "daily_signals", ["farm_id", "status"])

    op.create_table(
        "daily_tasks",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("farm_id", GUID(), sa.ForeignKey("farms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("signal_id", GUID(), sa.ForeignKey("daily_signals.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("merged_signal_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("task_type", sa.String(64), nullable=False),
        sa.Column("tier", sa.Integer(), nullable=False),
        sa.Column("rank_position", sa.Integer(), nullable=False),
        sa.Column("title_ta", sa.String(120), nullable=False),
        sa.Column("task_text_ta", sa.String(280), nullable=False),
        sa.Column("reason_text_ta", sa.String(280), nullable=False),
        sa.Column("why_am_i_seeing_this_ta", sa.String(400), nullable=False),
        sa.Column("field_label", sa.String(120), nullable=True),
        sa.Column("urgency", sa.String(16), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snoozed_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_channels", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("verification_followup_sent_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_daily_tasks_farm_id", "daily_tasks", ["farm_id"])
    op.create_index("ix_daily_tasks_user_id", "daily_tasks", ["user_id"])
    op.create_index("ix_daily_tasks_task_type", "daily_tasks", ["task_type"])
    op.create_index("ix_daily_tasks_status", "daily_tasks", ["status"])
    op.create_index(
        "ix_daily_task_user_status_created", "daily_tasks", ["user_id", "status", "created_at"]
    )

    op.create_table(
        "daily_task_responses",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("task_id", GUID(), sa.ForeignKey("daily_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("response_type", sa.String(32), nullable=False),
        sa.Column("structured_followup", sa.JSON(), nullable=True),
        sa.Column("photo_object_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("voice_note_object_id", sa.String(512), nullable=True),
        sa.Column("note_text", sa.Text(), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_daily_task_responses_task_id", "daily_task_responses", ["task_id"])

    op.create_table(
        "daily_task_zones",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("farm_id", GUID(), sa.ForeignKey("farms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_zone_id", sa.String(64), nullable=False),
        sa.Column("geometry", sa.JSON(), nullable=True),
        sa.Column("area_fraction", sa.Float(), nullable=False, server_default="0"),
        sa.Column("cardinal_label", sa.String(32), nullable=False),
        sa.Column("priority", sa.String(32), nullable=False, server_default="inspect_first"),
        sa.Column("first_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consecutive_confirming_scans", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(24), nullable=False, server_default="watching"),
        *_timestamps(),
        sa.UniqueConstraint("farm_id", "source_zone_id", name="uq_daily_task_zone_farm_source"),
    )
    op.create_index("ix_daily_task_zones_farm_id", "daily_task_zones", ["farm_id"])

    op.create_table(
        "evidence_packs",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("farm_id", GUID(), sa.ForeignKey("farms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("triggering_signal_id", GUID(), sa.ForeignKey("daily_signals.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("event_date_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_date_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confidence_level", sa.String(16), nullable=False),
        sa.Column("has_pre_event_imagery", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("has_post_event_imagery", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("imagery_degraded_reason", sa.String(120), nullable=True),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("pdf_object_url", sa.String(512), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending_post_event_data"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("shared_with", sa.JSON(), nullable=False, server_default="[]"),
        *_timestamps(),
    )
    op.create_index("ix_evidence_packs_farm_id", "evidence_packs", ["farm_id"])
    op.create_index("ix_evidence_packs_user_id", "evidence_packs", ["user_id"])

    op.create_table(
        "daily_task_audit_log",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("run_id", GUID(), nullable=False),
        sa.Column("farm_id", GUID(), nullable=False),
        sa.Column("signal_id", GUID(), nullable=True),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("decision_detail", sa.JSON(), nullable=False, server_default="{}"),
        *_timestamps(),
    )
    op.create_index("ix_daily_task_audit_log_run_id", "daily_task_audit_log", ["run_id"])
    op.create_index("ix_daily_task_audit_log_farm_id", "daily_task_audit_log", ["farm_id"])


def downgrade() -> None:
    op.drop_table("daily_task_audit_log")
    op.drop_table("evidence_packs")
    op.drop_table("daily_task_zones")
    op.drop_table("daily_task_responses")
    op.drop_table("daily_tasks")
    op.drop_table("daily_signals")
