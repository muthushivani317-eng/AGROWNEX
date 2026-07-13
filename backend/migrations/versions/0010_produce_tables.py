"""produce (sell my produce / procurement intelligence) tables

Revision ID: 0010_produce_tables
Revises: 0009_scheme_tables
Create Date: 2026-07-11
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_produce_tables"
down_revision: str | None = "0009_scheme_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    now = sa.func.now()

    op.create_table(
        "produce_offers",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=False),
        sa.Column("crop_session_id", UUID, nullable=True),
        sa.Column("crop_name", sa.String(80), nullable=False),
        sa.Column("variety", sa.String(80), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(12), nullable=False),
        sa.Column("expected_harvest_date", sa.Date(), nullable=False),
        sa.Column("expected_grade", sa.String(12), nullable=True),
        sa.Column("asking_price", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("current_market_price_snapshot", sa.Float(), nullable=True),
        sa.Column("market_price_min", sa.Float(), nullable=True),
        sa.Column("market_price_max", sa.Float(), nullable=True),
        sa.Column("market_price_unit", sa.String(12), nullable=True),
        sa.Column("market_price_source", sa.String(40), nullable=True),
        sa.Column("market_price_date", sa.Date(), nullable=True),
        sa.Column("available_from", sa.Date(), nullable=True),
        sa.Column("available_until", sa.Date(), nullable=True),
        sa.Column("district", sa.String(80), nullable=True),
        sa.Column("block", sa.String(80), nullable=True),
        sa.Column("village", sa.String(80), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(12), nullable=False, server_default="submitted"),
        sa.Column("procurement_channel", sa.String(20), nullable=True),
        sa.Column("procurement_reference", sa.String(80), nullable=True),
        sa.Column("ai_grade", sa.JSON(), nullable=True),
        sa.Column("buyer_match", sa.JSON(), nullable=True),
        sa.Column("logistics", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("idx_produce_offers_user", "produce_offers", ["user_id"])
    op.create_index("idx_produce_offers_farm", "produce_offers", ["farm_id"])
    op.create_index("idx_produce_offers_crop", "produce_offers", ["crop_name"])
    op.create_index("idx_produce_offers_status", "produce_offers", ["status"])
    op.create_index("idx_produce_offers_harvest", "produce_offers", ["expected_harvest_date"])
    op.create_index("idx_produce_offers_district", "produce_offers", ["district"])
    op.create_index("idx_produce_offers_session", "produce_offers", ["crop_session_id"])

    op.create_table(
        "offer_images",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("offer_id", UUID, sa.ForeignKey("produce_offers.id"), nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("image_url", sa.String(512), nullable=False),
        sa.Column("thumbnail_url", sa.String(512), nullable=True),
        sa.Column("mime_type", sa.String(80), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("caption", sa.String(255), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index("idx_offer_images_offer", "offer_images", ["offer_id"])
    op.create_index("idx_offer_images_user", "offer_images", ["user_id"])

    op.create_table(
        "offer_status_history",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("offer_id", UUID, sa.ForeignKey("produce_offers.id"), nullable=False),
        sa.Column("old_status", sa.String(12), nullable=True),
        sa.Column("new_status", sa.String(12), nullable=False),
        sa.Column("changed_by", UUID, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("note", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    )
    op.create_index(
        "idx_offer_status_history_offer", "offer_status_history", ["offer_id"]
    )

    op.create_table(
        "buyer_interest",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("offer_id", UUID, sa.ForeignKey("produce_offers.id"), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("buyer_name", sa.String(160), nullable=True),
        sa.Column("buyer_type", sa.String(20), nullable=True),
        sa.Column("contact", sa.String(120), nullable=True),
        sa.Column("offered_price", sa.Float(), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("external_reference", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("idx_buyer_interest_offer", "buyer_interest", ["offer_id"])


def downgrade() -> None:
    op.drop_table("buyer_interest")
    op.drop_table("offer_status_history")
    op.drop_table("offer_images")
    op.drop_table("produce_offers")
