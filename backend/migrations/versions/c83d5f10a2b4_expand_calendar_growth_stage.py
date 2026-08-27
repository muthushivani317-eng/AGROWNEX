"""Expand calendar growth-stage codes.

Revision ID: c83d5f10a2b4
Revises: a72f84c19e30
"""

import sqlalchemy as sa
from alembic import op

revision = "c83d5f10a2b4"
down_revision = "a72f84c19e30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "crop_calendar_events",
        "growth_stage",
        existing_type=sa.String(length=20),
        type_=sa.String(length=40),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "crop_calendar_events",
        "growth_stage",
        existing_type=sa.String(length=40),
        type_=sa.String(length=20),
        existing_nullable=False,
    )
