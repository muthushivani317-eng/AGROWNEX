"""add disease report conventional-category fields

Revision ID: 1ae3bce50f2a
Revises: d1a9f4c8b2e7
"""
from alembic import op
import sqlalchemy as sa

revision: str = "1ae3bce50f2a"
down_revision: str | None = "d1a9f4c8b2e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "disease_reports",
        sa.Column("conventional_category_english", sa.Text(), nullable=True),
    )
    op.add_column(
        "disease_reports",
        sa.Column("conventional_category_tamil", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("disease_reports", "conventional_category_tamil")
    op.drop_column("disease_reports", "conventional_category_english")
