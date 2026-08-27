"""Expand disease-risk qualitative confidence labels.

Revision ID: a72f84c19e30
Revises: f12a6c7e9b10
"""

import sqlalchemy as sa
from alembic import op

revision = "a72f84c19e30"
down_revision = "f12a6c7e9b10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "disease_risk_alerts",
        "confidence",
        existing_type=sa.String(length=30),
        type_=sa.String(length=50),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "disease_risk_alerts",
        "confidence",
        existing_type=sa.String(length=50),
        type_=sa.String(length=30),
        existing_nullable=False,
    )
