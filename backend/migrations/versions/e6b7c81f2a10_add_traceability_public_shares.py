"""add traceability public shares

Revision ID: e6b7c81f2a10
Revises: e5a9c72f3d01
"""

import sqlalchemy as sa
from alembic import op

revision = "e6b7c81f2a10"
down_revision = "e5a9c72f3d01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "produce_trace_shares",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("consent_fields", sa.JSON(), nullable=False),
        sa.Column("create_idempotency_key", sa.String(100), nullable=False),
        sa.Column("revoke_idempotency_key", sa.String(100)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["produce_trace_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("batch_id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "ix_produce_trace_shares_batch_id", "produce_trace_shares", ["batch_id"], unique=True
    )
    op.create_index(
        "ix_produce_trace_shares_owner_user_id", "produce_trace_shares", ["owner_user_id"]
    )
    op.create_index(
        "ix_produce_trace_shares_token_hash", "produce_trace_shares", ["token_hash"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_produce_trace_shares_token_hash", table_name="produce_trace_shares")
    op.drop_index("ix_produce_trace_shares_owner_user_id", table_name="produce_trace_shares")
    op.drop_index("ix_produce_trace_shares_batch_id", table_name="produce_trace_shares")
    op.drop_table("produce_trace_shares")
