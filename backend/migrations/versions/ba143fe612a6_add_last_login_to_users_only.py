"""add last_login to users only

Revision ID: ba143fe612a6
Revises: 0021_device_tokens
Create Date: 2026-07-17 12:43:24.531562
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'ba143fe612a6'
down_revision: str | None = '0021_device_tokens'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('last_login', sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('users', 'last_login')
