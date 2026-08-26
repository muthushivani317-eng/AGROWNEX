"""add stable farmer and produce listing references

Revision ID: e8c2f11a7d40
Revises: d4a7c91e5b20
"""

import sqlalchemy as sa
from alembic import op

revision = "e8c2f11a7d40"
down_revision = "d4a7c91e5b20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    postgres = bind.dialect.name == "postgresql"

    if postgres:
        op.execute("CREATE SEQUENCE agrowai_farmer_ref_seq START WITH 1")
        op.execute("CREATE SEQUENCE agrowai_produce_ref_seq START WITH 1")

    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("farmer_ref", sa.String(24), nullable=True))
    with op.batch_alter_table("produce_offers") as batch:
        batch.add_column(sa.Column("listing_ref", sa.String(32), nullable=True))

    if postgres:
        op.execute(
            "UPDATE users SET farmer_ref = 'AGF-' || "
            "lpad(nextval('agrowai_farmer_ref_seq')::text, 6, '0') "
            "WHERE farmer_ref IS NULL"
        )
        op.execute(
            "UPDATE produce_offers SET listing_ref = 'AGP-' || "
            "to_char(created_at, 'YYYY') || '-' || "
            "lpad(nextval('agrowai_produce_ref_seq')::text, 5, '0') "
            "WHERE listing_ref IS NULL"
        )
        farmer_default = sa.text(
            "'AGF-' || lpad(nextval('agrowai_farmer_ref_seq')::text, 6, '0')"
        )
        listing_default = sa.text(
            "'AGP-' || to_char(CURRENT_DATE, 'YYYY') || '-' || "
            "lpad(nextval('agrowai_produce_ref_seq')::text, 5, '0')"
        )
    else:
        op.execute(
            "UPDATE users SET farmer_ref = 'AGF-' || substr(replace(id, '-', ''), 1, 9) "
            "WHERE farmer_ref IS NULL"
        )
        op.execute(
            "UPDATE produce_offers SET listing_ref = 'AGP-' || "
            "strftime('%Y', created_at) || '-' || substr(replace(id, '-', ''), 1, 9) "
            "WHERE listing_ref IS NULL"
        )
        farmer_default = None
        listing_default = None

    with op.batch_alter_table("users") as batch:
        batch.alter_column("farmer_ref", nullable=False, server_default=farmer_default)
        batch.create_unique_constraint("uq_users_farmer_ref", ["farmer_ref"])
    with op.batch_alter_table("produce_offers") as batch:
        batch.alter_column("listing_ref", nullable=False, server_default=listing_default)
        batch.create_unique_constraint("uq_produce_offers_listing_ref", ["listing_ref"])


def downgrade() -> None:
    with op.batch_alter_table("produce_offers") as batch:
        batch.drop_constraint("uq_produce_offers_listing_ref", type_="unique")
        batch.drop_column("listing_ref")
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("uq_users_farmer_ref", type_="unique")
        batch.drop_column("farmer_ref")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP SEQUENCE agrowai_produce_ref_seq")
        op.execute("DROP SEQUENCE agrowai_farmer_ref_seq")
