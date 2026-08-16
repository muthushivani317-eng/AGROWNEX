"""add disease report review fields

Revision ID: e18a0d8f4c21
Revises: d7cf32746e8b
"""
from alembic import op
import sqlalchemy as sa

revision: str = "e18a0d8f4c21"
down_revision: str | None = "d7cf32746e8b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("disease_reports", "image_url", existing_type=sa.String(512), nullable=True)
    op.add_column("disease_reports", sa.Column("review_status", sa.String(20), nullable=True))
    op.add_column("disease_reports", sa.Column("reviewer_role", sa.String(30), nullable=True))
    op.add_column("disease_reports", sa.Column("corrected_label", sa.String(120), nullable=True))
    op.add_column("disease_reports", sa.Column("review_timestamp", sa.DateTime(timezone=True), nullable=True))
    op.add_column("disease_reports", sa.Column("review_consent", sa.Boolean(), nullable=True))
    op.add_column("disease_reports", sa.Column("kvk_session", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_index("ix_disease_reports_review_status", "disease_reports", ["review_status"])


def downgrade() -> None:
    op.drop_index("ix_disease_reports_review_status", table_name="disease_reports")
    for name in ("kvk_session", "review_consent", "review_timestamp", "corrected_label", "reviewer_role", "review_status"):
        op.drop_column("disease_reports", name)
    op.alter_column("disease_reports", "image_url", existing_type=sa.String(512), nullable=False)
