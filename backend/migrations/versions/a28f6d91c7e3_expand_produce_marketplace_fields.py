"""expand agricultural produce marketplace fields

Revision ID: a28f6d91c7e3
Revises: c83d5f10a2b4
"""

import sqlalchemy as sa
from alembic import op

revision = "a28f6d91c7e3"
down_revision = "c83d5f10a2b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    unique_names = {
        item.get("name")
        for item in sa.inspect(bind).get_unique_constraints("procurement_cases")
    }
    if "uq_procurement_case_offer" not in unique_names:
        duplicate = bind.execute(
            sa.text(
                "SELECT offer_id FROM procurement_cases GROUP BY offer_id "
                "HAVING COUNT(*) > 1 LIMIT 1"
            )
        ).first()
        if duplicate is not None:
            raise RuntimeError(
                "Cannot enforce procurement case uniqueness: duplicate offer_id rows exist"
            )
        with op.batch_alter_table("procurement_cases") as batch:
            batch.create_unique_constraint("uq_procurement_case_offer", ["offer_id"])
    with op.batch_alter_table("produce_offers") as batch:
        batch.add_column(sa.Column("product_category", sa.String(32), nullable=True))
        batch.add_column(sa.Column("availability_type", sa.String(24), nullable=True))
        batch.add_column(sa.Column("packaging", sa.String(160), nullable=True))
        batch.add_column(sa.Column("price_unit", sa.String(24), nullable=True))
        batch.add_column(
            sa.Column("negotiable", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch.add_column(
            sa.Column("pickup_available", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch.add_column(sa.Column("pickup_location", sa.String(255), nullable=True))
        batch.alter_column("expected_harvest_date", existing_type=sa.Date(), nullable=True)

    # Preserve old listings exactly while giving new code a stable taxonomy.
    op.execute(
        "UPDATE produce_offers SET product_category = 'other_produce' "
        "WHERE product_category IS NULL"
    )
    op.execute(
        "UPDATE produce_offers SET availability_type = 'upcoming_harvest' "
        "WHERE availability_type IS NULL"
    )
    with op.batch_alter_table("produce_offers") as batch:
        batch.alter_column("product_category", nullable=False, server_default="other_produce")
        batch.alter_column("availability_type", nullable=False, server_default="upcoming_harvest")
        batch.create_index("ix_produce_offers_product_category", ["product_category"])
        batch.create_index("ix_produce_offers_availability_type", ["availability_type"])


def downgrade() -> None:
    # Rows created as available-now have no harvest date; use their availability
    # date (or creation date) before restoring the legacy NOT NULL contract.
    op.execute(
        "UPDATE produce_offers SET expected_harvest_date = "
        "COALESCE(available_from, CAST(created_at AS DATE)) WHERE expected_harvest_date IS NULL"
    )
    with op.batch_alter_table("produce_offers") as batch:
        batch.drop_index("ix_produce_offers_availability_type")
        batch.drop_index("ix_produce_offers_product_category")
        batch.alter_column("expected_harvest_date", existing_type=sa.Date(), nullable=False)
        for column in (
            "pickup_location", "pickup_available", "negotiable", "price_unit",
            "packaging", "availability_type", "product_category",
        ):
            batch.drop_column(column)
