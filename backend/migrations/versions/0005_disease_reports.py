"""disease reports table

Revision ID: 0005_disease_reports
Revises: 0004_ai_chat_tables
Create Date: 2026-07-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_disease_reports"
down_revision: str | None = "0004_ai_chat_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    now = sa.func.now()
    op.create_table(
        "disease_reports",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=True),
        sa.Column("crop_session_id", UUID, nullable=True),
        sa.Column("image_url", sa.String(512), nullable=False),
        sa.Column("thumbnail_url", sa.String(512), nullable=True),
        sa.Column("capture_method", sa.String(20), server_default="gallery"),
        sa.Column("crop", sa.String(80), nullable=True),
        sa.Column("crop_confidence", sa.Integer(), nullable=True),
        sa.Column("disease", sa.String(200), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=True),
        sa.Column("severity", sa.String(20), nullable=True),
        sa.Column("symptoms", sa.JSON(), nullable=True),
        sa.Column("causes", sa.JSON(), nullable=True),
        sa.Column("recommendations", sa.JSON(), nullable=True),
        sa.Column("prevention", sa.JSON(), nullable=True),
        sa.Column("visible_parts", sa.JSON(), nullable=True),
        sa.Column(
            "needs_expert_review",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("explanation_tamil", sa.Text(), nullable=True),
        sa.Column("explanation_english", sa.Text(), nullable=True),
        sa.Column("model_used", sa.String(60), nullable=True),
        sa.Column("raw_response", sa.JSON(), nullable=True),
        sa.Column("weather_snapshot", sa.JSON(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("language", sa.String(5), nullable=False, server_default="ta"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("idx_disease_reports_user", "disease_reports", ["user_id"])
    op.create_index("idx_disease_reports_farm", "disease_reports", ["farm_id"])
    op.create_index("idx_disease_reports_crop", "disease_reports", ["crop"])
    op.create_index("idx_disease_reports_created", "disease_reports", ["created_at"])


def downgrade() -> None:
    op.drop_table("disease_reports")
