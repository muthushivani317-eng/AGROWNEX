"""market tables

Revision ID: 0007_market_tables
Revises: 0006_crop_calendar_events
Create Date: 2026-07-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_market_tables"
down_revision: str | None = "0006_crop_calendar_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    now = sa.func.now()

    op.create_table(
        "market_locations",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("market_name", sa.String(160), nullable=False),
        sa.Column("district", sa.String(120), nullable=False),
        sa.Column("state", sa.String(120), nullable=False),
        sa.Column("block", sa.String(120), nullable=True),
        sa.Column("village", sa.String(120), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("status", sa.String(12), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.UniqueConstraint(
            "market_name", "district", "state", name="uq_market_location"
        ),
    )
    op.create_index("idx_market_locations_name", "market_locations", ["market_name"])
    op.create_index("idx_market_locations_district", "market_locations", ["district"])
    op.create_index("idx_market_locations_state", "market_locations", ["state"])

    op.create_table(
        "market_prices",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "market_id", UUID, sa.ForeignKey("market_locations.id"), nullable=False
        ),
        sa.Column("commodity", sa.String(120), nullable=False),
        sa.Column("variety", sa.String(120), nullable=False, server_default=""),
        sa.Column("grade", sa.String(60), nullable=True),
        sa.Column("category", sa.String(20), nullable=False, server_default="other"),
        sa.Column("minimum_price", sa.Float(), nullable=False),
        sa.Column("maximum_price", sa.Float(), nullable=False),
        sa.Column("modal_price", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(12), nullable=False, server_default="quintal"),
        sa.Column("price_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.UniqueConstraint(
            "market_id", "commodity", "variety", "price_date", name="uq_market_price_day"
        ),
    )
    op.create_index("idx_market_prices_market", "market_prices", ["market_id"])
    op.create_index("idx_market_prices_commodity", "market_prices", ["commodity"])
    op.create_index("idx_market_prices_date", "market_prices", ["price_date"])

    op.create_table(
        "market_price_history",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "market_id", UUID, sa.ForeignKey("market_locations.id"), nullable=False
        ),
        sa.Column("commodity", sa.String(120), nullable=False),
        sa.Column("variety", sa.String(120), nullable=False, server_default=""),
        sa.Column("minimum_price", sa.Float(), nullable=False),
        sa.Column("maximum_price", sa.Float(), nullable=False),
        sa.Column("modal_price", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(12), nullable=False, server_default="quintal"),
        sa.Column("recorded_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.UniqueConstraint(
            "market_id",
            "commodity",
            "variety",
            "recorded_date",
            name="uq_market_history_day",
        ),
    )
    op.create_index(
        "idx_market_history_market", "market_price_history", ["market_id"]
    )
    op.create_index(
        "idx_market_history_commodity", "market_price_history", ["commodity"]
    )
    op.create_index(
        "idx_market_history_date", "market_price_history", ["recorded_date"]
    )

    op.create_table(
        "market_favourites",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("commodity", sa.String(120), nullable=False),
        sa.Column("market_name", sa.String(160), nullable=False),
        sa.Column("district", sa.String(120), nullable=False),
        sa.Column("state", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint(
            "user_id", "commodity", "market_name", "district", name="uq_market_favourite"
        ),
    )
    op.create_index("idx_market_favourites_user", "market_favourites", ["user_id"])


def downgrade() -> None:
    op.drop_table("market_favourites")
    op.drop_table("market_price_history")
    op.drop_table("market_prices")
    op.drop_table("market_locations")
