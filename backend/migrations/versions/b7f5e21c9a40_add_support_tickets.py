"""add farmer support tickets

Revision ID: b7f5e21c9a40
Revises: a28f6d91c7e3
"""

import sqlalchemy as sa
from alembic import op

from app.shared.base_model import GUID

revision = "b7f5e21c9a40"
down_revision = "a28f6d91c7e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "support_tickets",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("subject", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(16), nullable=False, server_default="normal"),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("app_version", sa.String(40)),
        sa.Column("device_context", sa.String(160)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_support_tickets_user_id", "support_tickets", ["user_id"])
    op.create_index("ix_support_tickets_status", "support_tickets", ["status"])
    op.create_index("ix_support_tickets_category", "support_tickets", ["category"])
    op.create_table(
        "support_ticket_messages",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column(
            "ticket_id",
            GUID(),
            sa.ForeignKey("support_tickets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("author_type", sa.String(16), nullable=False),
        sa.Column("author_user_id", GUID(), sa.ForeignKey("users.id")),
        sa.Column("author_admin_id", GUID(), sa.ForeignKey("admin_users.id")),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_support_ticket_messages_ticket_id", "support_ticket_messages", ["ticket_id"]
    )


def downgrade() -> None:
    op.drop_table("support_ticket_messages")
    op.drop_table("support_tickets")
