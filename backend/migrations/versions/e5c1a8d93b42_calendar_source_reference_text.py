"""widen crop_calendar_events.registry_source_reference to text

Verified schedule document references exceed 240 chars (paddy 257, tomato
1039), which made POST /api/v1/calendar/generate fail with
StringDataRightTruncationError.

Revision ID: e5c1a8d93b42
Revises: c3a8f1e6d2b7
"""

import sqlalchemy as sa
from alembic import op

revision = "e5c1a8d93b42"
down_revision = "c3a8f1e6d2b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "crop_calendar_events",
        "registry_source_reference",
        existing_type=sa.String(length=240),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.execute(
        "UPDATE crop_calendar_events SET registry_source_reference = "
        "LEFT(registry_source_reference, 240) "
        "WHERE length(registry_source_reference) > 240"
    )
    op.alter_column(
        "crop_calendar_events",
        "registry_source_reference",
        existing_type=sa.Text(),
        type_=sa.String(length=240),
        existing_nullable=True,
    )
