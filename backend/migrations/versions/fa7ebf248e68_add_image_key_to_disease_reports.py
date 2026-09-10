"""add_image_key_to_disease_reports

Revision ID: fa7ebf248e68
Revises: e6b7c81f2a10
Create Date: 2026-09-10 08:51:28.567415
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'fa7ebf248e68'
down_revision: str | None = 'e6b7c81f2a10'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("disease_reports", sa.Column("image_key", sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column("disease_reports", "image_key")
