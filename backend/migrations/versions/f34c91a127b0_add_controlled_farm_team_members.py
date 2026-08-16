"""add controlled farm team members

Revision ID: f34c91a127b0
Revises: e18a0d8f4c21
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f34c91a127b0"
down_revision: str | None = "e18a0d8f4c21"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    op.create_table(
        "farm_team_members",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "farm_id",
            uuid_type,
            sa.ForeignKey("farms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            uuid_type,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("added_by", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("farm_id", "user_id", name="uq_farm_team_member"),
    )
    op.create_index("ix_farm_team_members_farm_id", "farm_team_members", ["farm_id"])
    op.create_index("ix_farm_team_members_user_id", "farm_team_members", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_farm_team_members_user_id", table_name="farm_team_members")
    op.drop_index("ix_farm_team_members_farm_id", table_name="farm_team_members")
    op.drop_table("farm_team_members")
