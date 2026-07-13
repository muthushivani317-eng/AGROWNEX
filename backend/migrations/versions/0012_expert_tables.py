"""expert connect (consultation platform) tables

Revision ID: 0012_expert_tables
Revises: 0011_notification_tables
Create Date: 2026-07-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_expert_tables"
down_revision: str | None = "0011_notification_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    now = sa.func.now()

    op.create_table(
        "experts",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("expert_type", sa.String(24), nullable=False, server_default="tnau"),
        sa.Column("organization", sa.String(160), nullable=True),
        sa.Column("title", sa.String(120), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("photo_url", sa.String(512), nullable=True),
        sa.Column("districts", sa.JSON(), nullable=True),
        sa.Column("languages", sa.JSON(), nullable=True),
        sa.Column("years_experience", sa.Integer(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("rating_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(12), nullable=False, server_default="active"),
        sa.Column("slug", sa.String(120), nullable=True),
        sa.Column("source", sa.String(120), nullable=True),
        sa.Column("contact", sa.String(160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("idx_experts_user", "experts", ["user_id"])
    op.create_index("idx_experts_type", "experts", ["expert_type"])
    op.create_index("idx_experts_status", "experts", ["status"])
    op.create_index("idx_experts_slug", "experts", ["slug"])

    op.create_table(
        "expert_specializations",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("expert_id", UUID, sa.ForeignKey("experts.id"), nullable=False),
        sa.Column("category", sa.String(24), nullable=False),
        sa.Column("crop", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index(
        "idx_expert_specializations_expert", "expert_specializations", ["expert_id"]
    )
    op.create_index(
        "idx_expert_specializations_category", "expert_specializations", ["category"]
    )
    op.create_index("idx_expert_specializations_crop", "expert_specializations", ["crop"])

    op.create_table(
        "expert_availability",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("expert_id", UUID, sa.ForeignKey("experts.id"), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=True),
        sa.Column("start_time", sa.String(5), nullable=True),
        sa.Column("end_time", sa.String(5), nullable=True),
        sa.Column("timezone", sa.String(40), nullable=False, server_default="Asia/Kolkata"),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index(
        "idx_expert_availability_expert", "expert_availability", ["expert_id"]
    )

    op.create_table(
        "consultations",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("farmer_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=True),
        sa.Column("assigned_expert_id", UUID, sa.ForeignKey("experts.id"), nullable=True),
        sa.Column("crop_session_id", UUID, nullable=True),
        sa.Column("category", sa.String(24), nullable=False),
        sa.Column("crop", sa.String(80), nullable=True),
        sa.Column("subject", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(12), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(20), nullable=False, server_default="submitted"),
        sa.Column("channel", sa.String(12), nullable=False, server_default="in_app"),
        sa.Column("language", sa.String(8), nullable=False, server_default="ta"),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("idx_consultations_farmer", "consultations", ["farmer_id"])
    op.create_index("idx_consultations_farm", "consultations", ["farm_id"])
    op.create_index("idx_consultations_expert", "consultations", ["assigned_expert_id"])
    op.create_index("idx_consultations_category", "consultations", ["category"])
    op.create_index("idx_consultations_crop", "consultations", ["crop"])
    op.create_index("idx_consultations_status", "consultations", ["status"])
    op.create_index("idx_consultations_session", "consultations", ["crop_session_id"])

    op.create_table(
        "consultation_messages",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "consultation_id", UUID, sa.ForeignKey("consultations.id"), nullable=False
        ),
        sa.Column("sender_type", sa.String(8), nullable=False, server_default="farmer"),
        sa.Column("sender_user_id", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("sender_expert_id", UUID, sa.ForeignKey("experts.id"), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("language", sa.String(8), nullable=False, server_default="ta"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index(
        "idx_consultation_messages_consultation",
        "consultation_messages",
        ["consultation_id"],
    )

    op.create_table(
        "consultation_attachments",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "consultation_id", UUID, sa.ForeignKey("consultations.id"), nullable=False
        ),
        sa.Column(
            "message_id", UUID, sa.ForeignKey("consultation_messages.id"), nullable=True
        ),
        sa.Column("uploaded_by", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("kind", sa.String(12), nullable=False, server_default="image"),
        sa.Column("file_url", sa.String(512), nullable=False),
        sa.Column("thumbnail_url", sa.String(512), nullable=True),
        sa.Column("mime_type", sa.String(80), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("caption", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index(
        "idx_consultation_attachments_consultation",
        "consultation_attachments",
        ["consultation_id"],
    )
    op.create_index(
        "idx_consultation_attachments_message",
        "consultation_attachments",
        ["message_id"],
    )

    op.create_table(
        "consultation_status_history",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "consultation_id", UUID, sa.ForeignKey("consultations.id"), nullable=False
        ),
        sa.Column("old_status", sa.String(20), nullable=True),
        sa.Column("new_status", sa.String(20), nullable=False),
        sa.Column("changed_by_type", sa.String(8), nullable=False, server_default="system"),
        sa.Column("changed_by_id", UUID, nullable=True),
        sa.Column("note", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index(
        "idx_consultation_status_history_consultation",
        "consultation_status_history",
        ["consultation_id"],
    )


def downgrade() -> None:
    op.drop_table("consultation_status_history")
    op.drop_table("consultation_attachments")
    op.drop_table("consultation_messages")
    op.drop_table("consultations")
    op.drop_table("expert_availability")
    op.drop_table("expert_specializations")
    op.drop_table("experts")
