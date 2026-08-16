"""add farmer_documents table

Revision ID: d7cf32746e8b
Revises: 5ccb0904d5a5
Create Date: 2026-08-09 02:49:04.027581
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'd7cf32746e8b'
down_revision: str | None = '5ccb0904d5a5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    op.create_table(
        "farmer_documents",
        sa.Column(
            "id",
            uuid_type,
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            uuid_type,
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("document_type", sa.String(40), nullable=False),
        sa.Column(
            "has_document",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "user_id", "document_type", name="uq_farmer_document_type"
        ),
    )
    op.create_index(
        "ix_farmer_documents_user_id", "farmer_documents", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_farmer_documents_user_id", table_name="farmer_documents")
    op.drop_table("farmer_documents")
