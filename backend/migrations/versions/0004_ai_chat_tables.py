"""ai chat tables (ai_conversations, ai_messages)

Revision ID: 0004_ai_chat_tables
Revises: 0003_farm_tables
Create Date: 2026-07-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_ai_chat_tables"
down_revision: str | None = "0003_farm_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def _pk() -> sa.Column:
    return sa.Column(
        "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )


def _timestamps() -> list[sa.Column]:
    now = sa.func.now()
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "ai_conversations",
        _pk(),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=True),
        sa.Column("crop_session_id", UUID, nullable=True),
        sa.Column("title", sa.String(120), nullable=True),
        sa.Column("language", sa.String(5), nullable=False, server_default="ta"),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("idx_ai_conversations_user", "ai_conversations", ["user_id"])
    op.create_index("idx_ai_conversations_farm", "ai_conversations", ["farm_id"])

    op.create_table(
        "ai_messages",
        _pk(),
        sa.Column(
            "conversation_id",
            UUID,
            sa.ForeignKey("ai_conversations.id"),
            nullable=False,
        ),
        sa.Column("sender", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("language", sa.String(5), nullable=False, server_default="ta"),
        sa.Column("model_used", sa.String(60), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        *_timestamps(),
    )
    op.create_index("idx_ai_messages_conversation", "ai_messages", ["conversation_id"])


def downgrade() -> None:
    op.drop_table("ai_messages")
    op.drop_table("ai_conversations")
