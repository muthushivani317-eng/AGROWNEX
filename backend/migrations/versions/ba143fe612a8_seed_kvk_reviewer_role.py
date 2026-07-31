"""seed controlled KVK reviewer role

Revision ID: ba143fe612a8
Revises: ba143fe612a7
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "ba143fe612a8"
down_revision: str | None = "ba143fe612a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    roles = sa.table(
        "roles",
        sa.column("role_name", sa.String),
        sa.column("description", sa.String),
    )
    op.bulk_insert(
        roles,
        [
            {
                "role_name": "kvk_reviewer",
                "description": (
                    "Revocable KVK reviewer for controlled preliminary model testing"
                ),
            }
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM roles WHERE role_name = 'kvk_reviewer' "
            "AND NOT EXISTS ("
            "SELECT 1 FROM user_roles WHERE user_roles.role_id = roles.id"
            ")"
        )
    )
