"""Expand satellite unavailable reason for explicit provider states.

Revision ID: f07ad31c62b1
Revises: e28ab53c4d92
"""

import sqlalchemy as sa
from alembic import op

revision = "f07ad31c62b1"
down_revision = "e28ab53c4d92"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "satellite_sessions",
        "unavailable_reason",
        existing_type=sa.String(length=20),
        type_=sa.String(length=32),
        existing_nullable=False,
        existing_server_default="none",
    )


def downgrade() -> None:
    op.alter_column(
        "satellite_sessions",
        "unavailable_reason",
        existing_type=sa.String(length=32),
        type_=sa.String(length=20),
        existing_nullable=False,
        existing_server_default="none",
    )
