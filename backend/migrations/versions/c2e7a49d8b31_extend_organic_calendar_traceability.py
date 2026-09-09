"""extend organic calendar and produce traceability

Revision ID: c2e7a49d8b31
Revises: f1c8a34d9b72
"""
import sqlalchemy as sa
from alembic import op

revision = "c2e7a49d8b31"
down_revision = "f1c8a34d9b72"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "crop_calendar_events",
        sa.Column("organic_practice", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "produce_trace_batches",
        sa.Column(
            "cultivation_classification",
            sa.String(40),
            nullable=False,
            server_default="conventional",
        ),
    )
    op.add_column("produce_trace_batches", sa.Column("organic_profile_snapshot", sa.JSON()))
    op.add_column(
        "produce_trace_batches",
        sa.Column(
            "certification_verified_snapshot",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "produce_trace_batches",
        sa.Column(
            "classification_snapshotted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_column("produce_trace_batches", "classification_snapshotted_at")
    op.drop_column("produce_trace_batches", "certification_verified_snapshot")
    op.drop_column("produce_trace_batches", "organic_profile_snapshot")
    op.drop_column("produce_trace_batches", "cultivation_classification")
    op.drop_column("crop_calendar_events", "organic_practice")
