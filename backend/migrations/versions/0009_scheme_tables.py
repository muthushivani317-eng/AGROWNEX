"""government scheme tables

Revision ID: 0009_scheme_tables
Revises: 0008_crop_growth_tables
Create Date: 2026-07-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_scheme_tables"
down_revision: str | None = "0008_crop_growth_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    now = sa.func.now()

    op.create_table(
        "government_schemes",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("category", sa.String(30), nullable=False, server_default="other"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("benefits", sa.Text(), nullable=True),
        sa.Column("eligibility_summary", sa.Text(), nullable=True),
        sa.Column("application_steps", sa.JSON(), nullable=True),
        sa.Column("departments", sa.JSON(), nullable=True),
        sa.Column("official_url", sa.String(512), nullable=True),
        sa.Column("state", sa.String(80), nullable=False, server_default="all"),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("last_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(12), nullable=False, server_default="active"),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        # Structured eligibility rules evaluated by the engine.
        sa.Column("states", sa.JSON(), nullable=True),
        sa.Column("districts", sa.JSON(), nullable=True),
        sa.Column("crops", sa.JSON(), nullable=True),
        sa.Column("farmer_categories", sa.JSON(), nullable=True),
        sa.Column("min_land_hectares", sa.Float(), nullable=True),
        sa.Column("max_land_hectares", sa.Float(), nullable=True),
        sa.Column("max_annual_income", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(
        "idx_government_schemes_slug", "government_schemes", ["slug"], unique=True
    )
    op.create_index("idx_government_schemes_category", "government_schemes", ["category"])
    op.create_index("idx_government_schemes_state", "government_schemes", ["state"])
    op.create_index("idx_government_schemes_status", "government_schemes", ["status"])

    op.create_table(
        "scheme_documents",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "scheme_id",
            UUID,
            sa.ForeignKey("government_schemes.id"),
            nullable=False,
        ),
        sa.Column("document_name", sa.String(200), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index("idx_scheme_documents_scheme", "scheme_documents", ["scheme_id"])

    op.create_table(
        "scheme_bookmarks",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "scheme_id",
            UUID,
            sa.ForeignKey("government_schemes.id"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("user_id", "scheme_id", name="uq_scheme_bookmark"),
    )
    op.create_index("idx_scheme_bookmarks_user", "scheme_bookmarks", ["user_id"])
    op.create_index("idx_scheme_bookmarks_scheme", "scheme_bookmarks", ["scheme_id"])


def downgrade() -> None:
    op.drop_table("scheme_bookmarks")
    op.drop_table("scheme_documents")
    op.drop_table("government_schemes")
