"""add annual_income to farmer_profiles

Revision ID: 5ccb0904d5a5
Revises: ba143fe612a8
Create Date: 2026-08-08 23:23:01.825377
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '5ccb0904d5a5'
down_revision: str | None = 'ba143fe612a8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'farmer_profiles',
        sa.Column('annual_income', sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('farmer_profiles', 'annual_income')
