"""farm memory engine tables

Revision ID: 0017_memory_tables
Revises: 0016_intelligence_tables
Create Date: 2026-07-13
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017_memory_tables"
down_revision: str | None = "0016_intelligence_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    now = sa.func.now()

    op.create_table(
        "farm_memories",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=False),
        sa.Column("source_module", sa.String(24), nullable=False),
        sa.Column("event_type", sa.String(48), nullable=False),
        sa.Column("summary", sa.String(80), nullable=False),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("detail", sa.String(500), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=True),
        sa.Column("importance", sa.String(12), nullable=False, server_default="low"),
        sa.Column("importance_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("observation", sa.String(12), nullable=False, server_default="observed"),
        sa.Column("season", sa.String(12), nullable=True),
        sa.Column("season_year", sa.Integer(), nullable=True),
        sa.Column("crop", sa.String(80), nullable=True),
        sa.Column("location", sa.String(160), nullable=True),
        sa.Column("source_ref", sa.String(64), nullable=True),
        sa.Column("dedup_key", sa.String(160), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("embedding_ref", sa.String(120), nullable=True),
        sa.Column("embedding_model", sa.String(60), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("user_id", "dedup_key", name="uq_farm_memory_dedup"),
    )
    op.create_index("idx_memory_user", "farm_memories", ["user_id"])
    op.create_index("idx_memory_farm", "farm_memories", ["farm_id"])
    op.create_index("idx_memory_source", "farm_memories", ["source_module"])
    op.create_index("idx_memory_event_type", "farm_memories", ["event_type"])
    op.create_index("idx_memory_season", "farm_memories", ["season"])
    op.create_index("idx_memory_season_year", "farm_memories", ["season_year"])
    op.create_index("idx_memory_crop", "farm_memories", ["crop"])
    op.create_index("idx_memory_occurred", "farm_memories", ["occurred_at"])

    op.create_table(
        "memory_events",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("memory_id", UUID, sa.ForeignKey("farm_memories.id"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=False),
        sa.Column("source_module", sa.String(24), nullable=False),
        sa.Column("event_type", sa.String(48), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index("idx_memory_events_memory", "memory_events", ["memory_id"])
    op.create_index("idx_memory_events_user", "memory_events", ["user_id"])
    op.create_index("idx_memory_events_farm", "memory_events", ["farm_id"])

    op.create_table(
        "memory_embeddings",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("memory_id", UUID, sa.ForeignKey("farm_memories.id"), nullable=False),
        sa.Column("provider", sa.String(40), nullable=True),
        sa.Column("model", sa.String(60), nullable=True),
        sa.Column("dimensions", sa.Integer(), nullable=True),
        sa.Column("vector", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index("idx_memory_embeddings_memory", "memory_embeddings", ["memory_id"])

    op.create_table(
        "memory_tags",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("memory_id", UUID, sa.ForeignKey("farm_memories.id"), nullable=False),
        sa.Column("tag", sa.String(48), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.UniqueConstraint("memory_id", "tag", name="uq_memory_tag"),
    )
    op.create_index("idx_memory_tags_memory", "memory_tags", ["memory_id"])
    op.create_index("idx_memory_tags_tag", "memory_tags", ["tag"])

    op.create_table(
        "memory_summaries",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=False),
        sa.Column("period_type", sa.String(8), nullable=False),
        sa.Column("period_key", sa.String(24), nullable=False),
        sa.Column("season", sa.String(12), nullable=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("crop", sa.String(80), nullable=True),
        sa.Column("summary", sa.String(80), nullable=False),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("highlights", sa.JSON(), nullable=True),
        sa.Column("event_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("importance", sa.String(12), nullable=False, server_default="low"),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint(
            "user_id", "farm_id", "period_type", "period_key",
            name="uq_memory_summary_period",
        ),
    )
    op.create_index("idx_memory_summaries_user", "memory_summaries", ["user_id"])
    op.create_index("idx_memory_summaries_farm", "memory_summaries", ["farm_id"])
    op.create_index("idx_memory_summaries_year", "memory_summaries", ["year"])

    op.create_table(
        "memory_links",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("from_memory_id", UUID, sa.ForeignKey("farm_memories.id"), nullable=False),
        sa.Column("to_memory_id", UUID, sa.ForeignKey("farm_memories.id"), nullable=False),
        sa.Column("link_type", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.UniqueConstraint(
            "from_memory_id", "to_memory_id", "link_type", name="uq_memory_link"
        ),
    )
    op.create_index("idx_memory_links_user", "memory_links", ["user_id"])
    op.create_index("idx_memory_links_from", "memory_links", ["from_memory_id"])
    op.create_index("idx_memory_links_to", "memory_links", ["to_memory_id"])


def downgrade() -> None:
    op.drop_table("memory_links")
    op.drop_table("memory_summaries")
    op.drop_table("memory_tags")
    op.drop_table("memory_embeddings")
    op.drop_table("memory_events")
    op.drop_table("farm_memories")
