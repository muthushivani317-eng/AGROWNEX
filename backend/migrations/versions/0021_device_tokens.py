"""device tokens (FCM push — Phase 3)

Stores farmers' push device tokens so the FCM notification provider can deliver
to real devices.

Revision ID: 0021_device_tokens
Revises: 0020_hot_path_indexes
Create Date: 2026-07-13
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0021_device_tokens"
down_revision: str | None = "0020_hot_path_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    now = sa.func.now()
    op.create_table(
        "device_tokens",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token", sa.String(255), nullable=False),
        sa.Column("platform", sa.String(10), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=now, nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False
        ),
        sa.UniqueConstraint("token", name="uq_device_tokens_token"),
    )
    op.create_index("idx_device_tokens_user", "device_tokens", ["user_id"])
    op.create_index("idx_device_tokens_active", "device_tokens", ["is_active"])


def downgrade() -> None:
    op.drop_index("idx_device_tokens_active", table_name="device_tokens")
    op.drop_index("idx_device_tokens_user", table_name="device_tokens")
    op.drop_table("device_tokens")
