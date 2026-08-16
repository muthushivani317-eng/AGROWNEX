"""Add crop-stage registry lineage to calendar events.

Revision ID: 8df904e2c11a
Revises: 0b9a62c410df
"""

import sqlalchemy as sa
from alembic import op

revision = "8df904e2c11a"
down_revision = "0b9a62c410df"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("crop_calendar_events", sa.Column("registry_version", sa.String(40)))
    op.add_column("crop_calendar_events", sa.Column("registry_content_hash", sa.String(64)))


def downgrade() -> None:
    op.drop_column("crop_calendar_events", "registry_content_hash")
    op.drop_column("crop_calendar_events", "registry_version")
