"""token usage (AI cost control — Phase 1)

Records per-request AI token usage and estimated INR cost so the admin cost
dashboard can aggregate real spend per model and per module.

Revision ID: 0019_token_usage
Revises: 0018_admin_tables
Create Date: 2026-07-13
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019_token_usage"
down_revision: str | None = "0018_admin_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    now = sa.func.now()

    op.create_table(
        "token_usage",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("farmer_id", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("module", sa.String(40), nullable=False),
        sa.Column("model", sa.String(60), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False, server_default="gemini"),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "estimated_cost_inr",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "is_sample", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=now, nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False
        ),
    )
    op.create_index("idx_token_usage_farmer", "token_usage", ["farmer_id"])
    op.create_index("idx_token_usage_module", "token_usage", ["module"])
    op.create_index("idx_token_usage_model", "token_usage", ["model"])
    # Hot path for the cost dashboard: recent rows filtered by time.
    op.create_index("idx_token_usage_created", "token_usage", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_token_usage_created", table_name="token_usage")
    op.drop_index("idx_token_usage_model", table_name="token_usage")
    op.drop_index("idx_token_usage_module", table_name="token_usage")
    op.drop_index("idx_token_usage_farmer", table_name="token_usage")
    op.drop_table("token_usage")
