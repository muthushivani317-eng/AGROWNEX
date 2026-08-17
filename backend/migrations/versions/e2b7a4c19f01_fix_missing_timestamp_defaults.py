"""Fix missing server_default on created_at/updated_at for 9 tables.

Nine `create_table` migrations declared `created_at`/`updated_at` as
`nullable=False` without a `server_default`, even though every ORM model
declares `server_default=func.now()` via `TimestampMixin`
(app/shared/base_model.py). Because SQLAlchemy's INSERT compiler omits a
column with `server_default` set from the explicit column list (trusting
the database to supply it, then reads it back via RETURNING), any INSERT
into these tables fails with `NotNullViolationError: null value in column
"created_at"` -- there is no default in the live schema to satisfy it.

Confirmed live in AgrowAI-Production (2026-08-17): background
"weather_to_action" inserts into `action_workflows` were failing with
exactly this error, repeatedly poisoning the notification-sync request's
DB session (cascading 500s on GET /api/v1/notifications and
/notifications/unread) and contributing to slow/timed-out requests on
other endpoints sharing the connection pool. The same missing-default bug
in `crop_stage_states`/`crop_stage_transitions` and
`harvest_readiness_records`/`harvest_readiness_history` is the most likely
explanation for the Crop Calendar and Harvest Readiness screens always
showing "not available" -- their writes have been silently failing since
these tables were created.

This migration adds the missing `server_default=now()` to both columns on
all nine affected tables. It only changes the column default for future
inserts -- existing rows (all created via explicit application-level
timestamps where inserts happened to succeed) are untouched.

Revision ID: e2b7a4c19f01
Revises: f6a9c2e7410b
"""

import sqlalchemy as sa
from alembic import op

revision = "e2b7a4c19f01"
down_revision = "f6a9c2e7410b"
branch_labels = None
depends_on = None

AFFECTED_TABLES = [
    "waterlogging_assessments",
    "soil_indicator_evidence",
    "crop_stage_states",
    "crop_stage_transitions",
    "harvest_readiness_records",
    "harvest_readiness_history",
    "action_workflows",
    "action_audit_events",
    "soil_scan_records",
]


def upgrade() -> None:
    for table in AFFECTED_TABLES:
        op.alter_column(
            table,
            "created_at",
            server_default=sa.text("now()"),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
        )
        op.alter_column(
            table,
            "updated_at",
            server_default=sa.text("now()"),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
        )


def downgrade() -> None:
    for table in AFFECTED_TABLES:
        op.alter_column(
            table,
            "created_at",
            server_default=None,
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
        )
        op.alter_column(
            table,
            "updated_at",
            server_default=None,
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
        )
