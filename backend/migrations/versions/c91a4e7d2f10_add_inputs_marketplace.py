"""add buy-side inputs catalog and cash-delivery orders

Revision ID: c91a4e7d2f10
Revises: fa7ebf248e68
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c91a4e7d2f10"
down_revision: str | None = "fa7ebf248e68"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "input_catalog_items",
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("name_ta", sa.String(160)),
        sa.Column("category", sa.String(24), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("stock_quantity", sa.Integer(), nullable=False),
        sa.Column("stock_version", sa.Integer(), nullable=False),
        sa.Column("crop_tags", sa.String(500)),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.CheckConstraint("unit_price > 0", name="ck_input_catalog_price_positive"),
        sa.CheckConstraint("stock_quantity >= 0", name="ck_input_catalog_stock_nonnegative"),
        sa.CheckConstraint("stock_version > 0", name="ck_input_catalog_version_positive"),
    )
    op.create_index("ix_input_catalog_items_category", "input_catalog_items", ["category"])
    op.create_index("ix_input_catalog_items_is_active", "input_catalog_items", ["is_active"])
    op.create_index("ix_input_catalog_items_name", "input_catalog_items", ["name"])
    op.create_table(
        "input_orders",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("order_ref", sa.String(40), nullable=False, unique=True),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("delivery_address", sa.String(500), nullable=False),
        sa.Column("delivery_eta", sa.DateTime(timezone=True)),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("cash_collected_at", sa.DateTime(timezone=True)),
        sa.Column("cash_collected_by_admin_id", sa.Uuid(), sa.ForeignKey("admin_users.id")),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_input_order_user_idempotency"),
        sa.CheckConstraint("total_amount > 0", name="ck_input_order_total_positive"),
    )
    op.create_index("ix_input_orders_user_id", "input_orders", ["user_id"])
    op.create_index("ix_input_orders_status", "input_orders", ["status"])
    op.create_index("ix_input_orders_order_ref", "input_orders", ["order_ref"], unique=True)
    op.create_table(
        "input_order_items",
        sa.Column("order_id", sa.Uuid(), sa.ForeignKey("input_orders.id"), nullable=False),
        sa.Column(
            "catalog_item_id", sa.Uuid(), sa.ForeignKey("input_catalog_items.id"), nullable=False
        ),
        sa.Column("product_name_snapshot", sa.String(160), nullable=False),
        sa.Column("category_snapshot", sa.String(24), nullable=False),
        sa.Column("unit_snapshot", sa.String(32), nullable=False),
        sa.Column("unit_price_snapshot", sa.Numeric(14, 2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("line_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("quantity > 0", name="ck_input_order_item_quantity_positive"),
        sa.CheckConstraint("line_total > 0", name="ck_input_order_item_total_positive"),
    )
    op.create_index("ix_input_order_items_order_id", "input_order_items", ["order_id"])
    op.create_index(
        "ix_input_order_items_catalog_item_id", "input_order_items", ["catalog_item_id"]
    )
    op.create_table(
        "input_order_events",
        sa.Column("order_id", sa.Uuid(), sa.ForeignKey("input_orders.id"), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("old_status", sa.String(24)),
        sa.Column("new_status", sa.String(24)),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("actor_admin_id", sa.Uuid(), sa.ForeignKey("admin_users.id")),
        sa.Column("amount", sa.Numeric(14, 2)),
        sa.Column("note", sa.String(500)),
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_input_order_events_order_id", "input_order_events", ["order_id"])
    op.create_index("ix_input_order_events_event_type", "input_order_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("input_order_events")
    op.drop_table("input_order_items")
    op.drop_table("input_orders")
    op.drop_table("input_catalog_items")
