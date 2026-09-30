"""Onboarding v2: profile extras, farmer farm items, FPO/KVK directory.

- farmer_profiles: land_holding_acres, farmer_type, landmark, needs, needs_note
- farmer_farm_items: one row per crop / livestock / product a farmer declares
- organic_partner_organizations: district, listed_in_app (farmer "Join" list)

Revision ID: b7e2c9d4a1f0
Revises: 10f4bbda5d11
"""

import sqlalchemy as sa
from alembic import op

from app.shared.base_model import GUID

revision = "b7e2c9d4a1f0"
down_revision = "10f4bbda5d11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("farmer_profiles") as batch:
        batch.add_column(sa.Column("land_holding_acres", sa.Float(), nullable=True))
        batch.add_column(sa.Column("farmer_type", sa.String(30), nullable=True))
        batch.add_column(sa.Column("landmark", sa.String(160), nullable=True))
        batch.add_column(sa.Column("needs", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("needs_note", sa.String(300), nullable=True))

    op.create_table(
        "farmer_farm_items",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("item_code", sa.String(60), nullable=False),
        sa.Column("custom_name", sa.String(80), nullable=True),
        sa.Column("harvest_months", sa.JSON(), nullable=False),
        sa.Column("approx_quantity", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(16), nullable=True),
        sa.Column("area_acres", sa.Float(), nullable=True),
        sa.Column("available_for_sale", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_farmer_farm_items_user_id", "farmer_farm_items", ["user_id"])
    op.create_index("ix_farmer_farm_items_category", "farmer_farm_items", ["category"])
    op.create_index("ix_farmer_farm_items_item_code", "farmer_farm_items", ["item_code"])

    with op.batch_alter_table("organic_partner_organizations") as batch:
        batch.add_column(sa.Column("district", sa.String(80), nullable=True))
        batch.add_column(sa.Column("listed_in_app", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.create_index("ix_organic_partner_organizations_district", ["district"])


def downgrade() -> None:
    with op.batch_alter_table("organic_partner_organizations") as batch:
        batch.drop_index("ix_organic_partner_organizations_district")
        batch.drop_column("listed_in_app")
        batch.drop_column("district")
    op.drop_index("ix_farmer_farm_items_item_code", table_name="farmer_farm_items")
    op.drop_index("ix_farmer_farm_items_category", table_name="farmer_farm_items")
    op.drop_index("ix_farmer_farm_items_user_id", table_name="farmer_farm_items")
    op.drop_table("farmer_farm_items")
    with op.batch_alter_table("farmer_profiles") as batch:
        batch.drop_column("needs_note")
        batch.drop_column("needs")
        batch.drop_column("landmark")
        batch.drop_column("farmer_type")
        batch.drop_column("land_holding_acres")
