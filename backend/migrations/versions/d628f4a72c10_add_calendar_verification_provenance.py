"""add calendar verification provenance

Revision ID: d628f4a72c10
Revises: c41a79e5d211
"""

import sqlalchemy as sa
from alembic import op

revision = "d628f4a72c10"
down_revision = "c41a79e5d211"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "crop_calendar_events",
        sa.Column("registry_verification_status", sa.String(length=24), nullable=True),
    )
    op.add_column(
        "crop_calendar_events",
        sa.Column("registry_source_reference", sa.String(length=240), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("crop_calendar_events", "registry_source_reference")
    op.drop_column("crop_calendar_events", "registry_verification_status")
