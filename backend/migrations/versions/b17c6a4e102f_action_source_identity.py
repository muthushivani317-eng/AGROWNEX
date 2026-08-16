"""Prevent duplicate source actions.

Revision ID: b17c6a4e102f
Revises: a341fd7820cc
"""
from alembic import op

revision = "b17c6a4e102f"
down_revision = "a341fd7820cc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_action_source_identity",
        "action_workflows",
        ["user_id", "farm_id", "source_module", "source_record_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_action_source_identity", "action_workflows", type_="unique"
    )
