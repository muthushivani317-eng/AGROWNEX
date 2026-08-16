"""add controlled community qa

Revision ID: d12eb863ff71
Revises: c91f420ae814
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d12eb863ff71"
down_revision = "c91f420ae814"
branch_labels = None
depends_on = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),  # noqa: E501
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),  # noqa: E501
    ]


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "community_questions",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("author_user_id", uuid, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("crop", sa.String(80)),
        sa.Column("language", sa.String(8), server_default="ta", nullable=False),
        sa.Column("moderation_status", sa.String(20), server_default="active", nullable=False),  # noqa: E501
        sa.Column("report_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.false(), nullable=False),
        *timestamps(),
    )
    for column in ("author_user_id", "crop", "moderation_status"):
        op.create_index(f"ix_community_questions_{column}", "community_questions", [column])
    op.create_table(
        "community_answers",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "question_id",
            uuid,
            sa.ForeignKey("community_questions.id", ondelete="CASCADE"),
            nullable=False,
        ),  # noqa: E501
        sa.Column("author_user_id", uuid, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("language", sa.String(8), server_default="ta", nullable=False),
        sa.Column("moderation_status", sa.String(20), server_default="active", nullable=False),  # noqa: E501
        sa.Column("report_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.false(), nullable=False),
        *timestamps(),
    )
    for column in ("question_id", "author_user_id", "moderation_status"):
        op.create_index(f"ix_community_answers_{column}", "community_answers", [column])
    op.create_table(
        "community_reports",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("reporter_user_id", uuid, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("target_type", sa.String(12), nullable=False),
        sa.Column("target_id", uuid, nullable=False),
        sa.Column("reason", sa.String(40), nullable=False),
        *timestamps(),
        sa.UniqueConstraint(
            "reporter_user_id", "target_type", "target_id", name="uq_community_report"
        ),  # noqa: E501
    )
    op.create_index(
        "ix_community_reports_reporter_user_id", "community_reports", ["reporter_user_id"]
    )
    op.create_index("ix_community_reports_target_id", "community_reports", ["target_id"])


def downgrade() -> None:
    op.drop_table("community_reports")
    op.drop_table("community_answers")
    op.drop_table("community_questions")
