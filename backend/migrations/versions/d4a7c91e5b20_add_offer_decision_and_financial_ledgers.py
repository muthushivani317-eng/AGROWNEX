"""add frozen farmer decisions and procurement financial ledgers

Revision ID: d4a7c91e5b20
Revises: b91d0e6c4a32
"""

import sqlalchemy as sa
from alembic import op
from app.shared.base_model import GUID

revision = "d4a7c91e5b20"
down_revision = "b91d0e6c4a32"
branch_labels = None
depends_on = None


def _id():
    return sa.Column("id", GUID(), primary_key=True, nullable=False)


def _created():
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


def upgrade() -> None:
    with op.batch_alter_table("procurement_cases") as batch:
        batch.drop_constraint("ck_procurement_phase1_status", type_="check")
        batch.add_column(sa.Column("frozen_terms", sa.JSON()))
        batch.add_column(sa.Column("frozen_terms_hash", sa.String(64)))
        batch.add_column(sa.Column("frozen_at", sa.DateTime(timezone=True)))
        batch.create_unique_constraint("uq_procurement_frozen_terms_hash", ["frozen_terms_hash"])
        batch.create_check_constraint(
            "ck_procurement_phase1_status",
            "status IN ('new','under_review','farmer_contacted','finding_buyers',"
            "'buyer_interested','offer_received','farmer_approval_pending',"
            "'farmer_accepted','farmer_rejected','cancelled')",
        )

    op.create_table(
        "farmer_offer_decisions",
        _id(),
        sa.Column("case_id", GUID(), sa.ForeignKey("procurement_cases.id"), nullable=False),
        sa.Column("offer_id", GUID(), sa.ForeignKey("produce_offers.id"), nullable=False),
        sa.Column("farmer_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("terms_hash", sa.String(64), nullable=False),
        sa.Column("terms_snapshot", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column(
            "decided_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("case_id", name="uq_farmer_offer_decision_case"),
        sa.UniqueConstraint("farmer_id", "idempotency_key", name="uq_farmer_decision_idempotency"),
        sa.CheckConstraint("decision IN ('accepted','rejected')", name="ck_farmer_offer_decision"),
    )
    op.create_index("ix_farmer_offer_decisions_case_id", "farmer_offer_decisions", ["case_id"])
    op.create_index("ix_farmer_offer_decisions_offer_id", "farmer_offer_decisions", ["offer_id"])
    op.create_index("ix_farmer_offer_decisions_farmer_id", "farmer_offer_decisions", ["farmer_id"])

    op.create_table(
        "pickup_ledger",
        _id(),
        sa.Column("case_id", GUID(), sa.ForeignKey("procurement_cases.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True)),
        sa.Column("occurred_at", sa.DateTime(timezone=True)),
        sa.Column("location", sa.String(255)),
        sa.Column("note", sa.Text()),
        sa.Column("recorded_by_admin_id", GUID(), sa.ForeignKey("admin_users.id"), nullable=False),
        _created(),
        sa.CheckConstraint(
            "status IN ('scheduled','completed','failed','cancelled')",
            name="ck_pickup_ledger_status",
        ),
    )
    op.create_index("ix_pickup_ledger_case_id", "pickup_ledger", ["case_id"])

    op.create_table(
        "procurement_transactions",
        _id(),
        sa.Column("case_id", GUID(), sa.ForeignKey("procurement_cases.id"), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("gross_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("terms_hash", sa.String(64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by_admin_id", GUID(), sa.ForeignKey("admin_users.id"), nullable=False),
        _created(),
        sa.UniqueConstraint("case_id", name="uq_procurement_transaction_case"),
        sa.CheckConstraint("gross_amount > 0", name="ck_procurement_transaction_gross"),
    )
    op.create_index("ix_procurement_transactions_case_id", "procurement_transactions", ["case_id"])

    op.create_table(
        "payment_ledger",
        _id(),
        sa.Column(
            "transaction_id", GUID(), sa.ForeignKey("procurement_transactions.id"), nullable=False
        ),
        sa.Column("entry_type", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("reference", sa.String(160)),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by_admin_id", GUID(), sa.ForeignKey("admin_users.id"), nullable=False),
        _created(),
        sa.CheckConstraint("amount > 0", name="ck_payment_ledger_amount"),
        sa.CheckConstraint(
            "entry_type IN ('buyer_receipt','farmer_payout','refund')",
            name="ck_payment_ledger_type",
        ),
    )
    op.create_index("ix_payment_ledger_transaction_id", "payment_ledger", ["transaction_id"])

    op.create_table(
        "commission_ledger",
        _id(),
        sa.Column(
            "transaction_id", GUID(), sa.ForeignKey("procurement_transactions.id"), nullable=False
        ),
        sa.Column("entry_type", sa.String(16), nullable=False),
        sa.Column("base_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by_admin_id", GUID(), sa.ForeignKey("admin_users.id"), nullable=False),
        _created(),
        sa.CheckConstraint("amount >= 0", name="ck_commission_ledger_amount"),
        sa.CheckConstraint(
            "entry_type IN ('earned','reversed','paid')", name="ck_commission_ledger_type"
        ),
    )
    op.create_index("ix_commission_ledger_transaction_id", "commission_ledger", ["transaction_id"])


def downgrade() -> None:
    for table in (
        "commission_ledger",
        "payment_ledger",
        "procurement_transactions",
        "pickup_ledger",
        "farmer_offer_decisions",
    ):
        op.drop_table(table)
    with op.batch_alter_table("procurement_cases") as batch:
        batch.drop_constraint("ck_procurement_phase1_status", type_="check")
        batch.drop_constraint("uq_procurement_frozen_terms_hash", type_="unique")
        batch.drop_column("frozen_at")
        batch.drop_column("frozen_terms_hash")
        batch.drop_column("frozen_terms")
        batch.create_check_constraint(
            "ck_procurement_phase1_status",
            "status IN ('new','under_review','farmer_contacted','finding_buyers',"
            "'buyer_interested','offer_received','farmer_approval_pending','cancelled')",
        )
