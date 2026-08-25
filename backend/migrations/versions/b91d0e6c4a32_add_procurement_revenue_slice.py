"""add produce supply facts and internal procurement cases

Revision ID: b91d0e6c4a32
Revises: c8b4f7a21d09
"""

import sqlalchemy as sa
from alembic import op
from app.shared.base_model import GUID

revision = "b91d0e6c4a32"
down_revision = "c8b4f7a21d09"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable expansion preserves every pre-existing produce offer unchanged.
    # Batch mode is required for SQLite and emits ordinary ALTER TABLE statements
    # on PostgreSQL, keeping the migration portable across supported environments.
    with op.batch_alter_table("produce_offers") as batch:
        batch.add_column(sa.Column("cultivated_area_hectares", sa.Float()))
        batch.add_column(sa.Column("expected_total_quantity", sa.Float()))
        batch.add_column(sa.Column("available_quantity", sa.Float()))
        batch.add_column(sa.Column("quantity_provenance", sa.String(24)))
        batch.add_column(sa.Column("quality_notes", sa.Text()))
        batch.create_check_constraint(
            "ck_produce_area_positive",
            "cultivated_area_hectares IS NULL OR cultivated_area_hectares > 0",
        )
        batch.create_check_constraint(
            "ck_produce_expected_quantity_positive",
            "expected_total_quantity IS NULL OR expected_total_quantity > 0",
        )
        batch.create_check_constraint(
            "ck_produce_available_quantity_positive",
            "available_quantity IS NULL OR available_quantity > 0",
        )
        batch.create_check_constraint(
            "ck_produce_available_within_expected",
            "available_quantity IS NULL OR expected_total_quantity IS NULL OR "
            "available_quantity <= expected_total_quantity",
        )
        batch.create_check_constraint(
            "ck_produce_quantity_provenance",
            "quantity_provenance IS NULL OR quantity_provenance IN "
            "('farmer_reported','system_estimated','verified')",
        )
    op.create_table(
        "procurement_cases",
        sa.Column("offer_id", GUID(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="new"),
        sa.Column("assigned_admin_id", GUID()),
        sa.Column("follow_up_at", sa.DateTime(timezone=True)),
        sa.Column("buyer_name", sa.String(160)),
        sa.Column("buyer_contact", sa.String(160)),
        sa.Column("buyer_offer_quantity", sa.Float()),
        sa.Column("buyer_offer_price", sa.Numeric(14, 2)),
        sa.Column("transport_cost", sa.Numeric(14, 2)),
        sa.Column("commission_rate", sa.Numeric(5, 2)),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("price_unit", sa.String(16)),
        sa.Column("negotiation_notes", sa.Text()),
        sa.Column("id", GUID(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["assigned_admin_id"], ["admin_users.id"]),
        sa.ForeignKeyConstraint(["offer_id"], ["produce_offers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("offer_id", name="uq_procurement_case_offer"),
        sa.CheckConstraint(
            "buyer_offer_quantity IS NULL OR buyer_offer_quantity > 0",
            name="ck_procurement_offer_qty_positive",
        ),
        sa.CheckConstraint(
            "buyer_offer_price IS NULL OR buyer_offer_price > 0",
            name="ck_procurement_offer_price_positive",
        ),
        sa.CheckConstraint(
            "transport_cost IS NULL OR transport_cost >= 0",
            name="ck_procurement_transport_nonnegative",
        ),
        sa.CheckConstraint(
            "commission_rate IS NULL OR (commission_rate >= 0 AND commission_rate <= 100)",
            name="ck_procurement_commission_rate",
        ),
        sa.CheckConstraint(
            "status IN ('new','under_review','farmer_contacted','finding_buyers',"
            "'buyer_interested','offer_received','farmer_approval_pending','cancelled')",
            name="ck_procurement_phase1_status",
        ),
    )
    op.create_index("ix_procurement_cases_offer_id", "procurement_cases", ["offer_id"])
    op.create_index("ix_procurement_cases_status", "procurement_cases", ["status"])
    op.create_index(
        "ix_procurement_cases_assigned_admin_id", "procurement_cases", ["assigned_admin_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_procurement_cases_assigned_admin_id", table_name="procurement_cases")
    op.drop_index("ix_procurement_cases_status", table_name="procurement_cases")
    op.drop_index("ix_procurement_cases_offer_id", table_name="procurement_cases")
    op.drop_table("procurement_cases")
    with op.batch_alter_table("produce_offers") as batch:
        batch.drop_constraint("ck_produce_quantity_provenance", type_="check")
        batch.drop_constraint("ck_produce_available_within_expected", type_="check")
        batch.drop_constraint("ck_produce_available_quantity_positive", type_="check")
        batch.drop_constraint("ck_produce_expected_quantity_positive", type_="check")
        batch.drop_constraint("ck_produce_area_positive", type_="check")
        batch.drop_column("quality_notes")
        batch.drop_column("quantity_provenance")
        batch.drop_column("available_quantity")
        batch.drop_column("expected_total_quantity")
        batch.drop_column("cultivated_area_hectares")
