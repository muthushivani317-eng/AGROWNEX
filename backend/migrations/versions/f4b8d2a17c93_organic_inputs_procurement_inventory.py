"""Organic Inputs Marketplace procurement + inventory phase: offers, receipts,
inventory lots and movements.

Revision ID: f4b8d2a17c93
Revises: e7a2c94f0d1b
"""

from alembic import op
import sqlalchemy as sa

from app.shared.base_model import GUID

revision = "f4b8d2a17c93"
down_revision = "e7a2c94f0d1b"
branch_labels = None
depends_on = None


def _base():
    return [
        sa.Column("id", GUID(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade():
    op.create_table(
        "organic_inputs_batch_procurement_offers",
        *_base(),
        sa.Column(
            "batch_id",
            GUID(),
            sa.ForeignKey("organic_inputs_production_batches.id"),
            nullable=False,
        ),
        sa.Column("offered_quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.Column("offered_unit_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("offered_by_admin_id", GUID(), sa.ForeignKey("admin_users.id")),
        sa.Column("offered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("rejection_reason", sa.Text()),
        sa.UniqueConstraint("batch_id", name="uq_organic_inputs_offer_batch"),
        sa.CheckConstraint(
            "offered_quantity > 0", name="ck_organic_inputs_offer_quantity_positive"
        ),
        sa.CheckConstraint("offered_unit_price > 0", name="ck_organic_inputs_offer_price_positive"),
    )
    op.create_index(
        "ix_organic_inputs_offer_batch_id",
        "organic_inputs_batch_procurement_offers",
        ["batch_id"],
    )
    op.create_index(
        "ix_organic_inputs_offer_status",
        "organic_inputs_batch_procurement_offers",
        ["status"],
    )

    op.create_table(
        "organic_inputs_batch_receipts",
        *_base(),
        sa.Column(
            "batch_id",
            GUID(),
            sa.ForeignKey("organic_inputs_production_batches.id"),
            nullable=False,
        ),
        sa.Column(
            "offer_id",
            GUID(),
            sa.ForeignKey("organic_inputs_batch_procurement_offers.id"),
            nullable=False,
        ),
        sa.Column("received_quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.Column("received_by_admin_id", GUID(), sa.ForeignKey("admin_users.id")),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("condition_note", sa.Text()),
        sa.UniqueConstraint("offer_id", name="uq_organic_inputs_receipt_offer"),
        sa.CheckConstraint(
            "received_quantity > 0", name="ck_organic_inputs_receipt_quantity_positive"
        ),
    )
    op.create_index(
        "ix_organic_inputs_receipt_batch_id", "organic_inputs_batch_receipts", ["batch_id"]
    )

    op.create_table(
        "organic_inputs_inventory_lots",
        *_base(),
        sa.Column(
            "batch_id",
            GUID(),
            sa.ForeignKey("organic_inputs_production_batches.id"),
            nullable=False,
        ),
        sa.Column(
            "product_type_id",
            GUID(),
            sa.ForeignKey("organic_inputs_product_types.id"),
            nullable=False,
        ),
        sa.Column(
            "receipt_id",
            GUID(),
            sa.ForeignKey("organic_inputs_batch_receipts.id"),
            nullable=False,
        ),
        sa.Column("quantity_available", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.Column("unit_cost", sa.Numeric(14, 2), nullable=False),
        sa.UniqueConstraint("batch_id", name="uq_organic_inputs_inventory_lot_batch"),
        sa.CheckConstraint("quantity_available >= 0", name="ck_organic_inputs_lot_quantity_nonneg"),
    )
    op.create_index("ix_organic_inputs_lot_batch_id", "organic_inputs_inventory_lots", ["batch_id"])
    op.create_index(
        "ix_organic_inputs_lot_product_type_id",
        "organic_inputs_inventory_lots",
        ["product_type_id"],
    )

    op.create_table(
        "organic_inputs_inventory_movements",
        *_base(),
        sa.Column(
            "lot_id", GUID(), sa.ForeignKey("organic_inputs_inventory_lots.id"), nullable=False
        ),
        sa.Column("movement_type", sa.String(16), nullable=False),
        sa.Column("quantity_delta", sa.Numeric(14, 3), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("performed_by_admin_id", GUID(), sa.ForeignKey("admin_users.id")),
        sa.CheckConstraint("quantity_delta != 0", name="ck_organic_inputs_movement_delta_nonzero"),
    )
    op.create_index(
        "ix_organic_inputs_movement_lot_id", "organic_inputs_inventory_movements", ["lot_id"]
    )


def downgrade():
    op.drop_table("organic_inputs_inventory_movements")
    op.drop_table("organic_inputs_inventory_lots")
    op.drop_table("organic_inputs_batch_receipts")
    op.drop_table("organic_inputs_batch_procurement_offers")
