"""add controlled produce traceability

Revision ID: c91f420ae814
Revises: b68ed53d0f2a
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c91f420ae814"
down_revision = "b68ed53d0f2a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "produce_trace_batches",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "offer_id",
            uuid,
            sa.ForeignKey("produce_offers.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("owner_user_id", uuid, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("batch_code", sa.String(40), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),  # noqa: E501
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),  # noqa: E501
    )
    op.create_index(
        "ix_produce_trace_batches_offer_id",
        "produce_trace_batches",
        ["offer_id"],
        unique=True,
    )
    op.create_index(
        "ix_produce_trace_batches_owner_user_id",
        "produce_trace_batches",
        ["owner_user_id"],
    )
    op.create_index(
        "ix_produce_trace_batches_batch_code",
        "produce_trace_batches",
        ["batch_code"],
        unique=True,
    )
    op.create_table(
        "produce_trace_events",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("batch_id", uuid, sa.ForeignKey("produce_trace_batches.id", ondelete="CASCADE"), nullable=False),  # noqa: E501
        sa.Column("actor_user_id", uuid, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location_text", sa.String(160)),
        sa.Column("notes", sa.String(1000)),
        sa.Column("evidence_url", sa.String(512)),
        sa.Column("previous_hash", sa.String(64)),
        sa.Column("event_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),  # noqa: E501
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),  # noqa: E501
    )
    for column in ("batch_id", "actor_user_id", "event_type"):
        op.create_index(f"ix_produce_trace_events_{column}", "produce_trace_events", [column])


def downgrade() -> None:
    op.drop_table("produce_trace_events")
    op.drop_table("produce_trace_batches")
