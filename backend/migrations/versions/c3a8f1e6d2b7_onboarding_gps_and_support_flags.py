"""Onboarding v2 (app build): GPS and FPO/KVK support interest on the profile.

Replaces the app-side draft migration 2f8d7c1a9b40 (never deployed); its
land/farmer-type/landmark columns already exist from b7e2c9d4a1f0 and its
farm_products JSON is stored in farmer_farm_items instead.

Revision ID: c3a8f1e6d2b7
Revises: b7e2c9d4a1f0
"""

import sqlalchemy as sa
from alembic import op

revision = "c3a8f1e6d2b7"
down_revision = "b7e2c9d4a1f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("farmer_profiles") as batch:
        batch.add_column(sa.Column("latitude", sa.Float(), nullable=True))
        batch.add_column(sa.Column("longitude", sa.Float(), nullable=True))
        batch.add_column(sa.Column("wants_fpo_support", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("wants_kvk_support", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table("farmer_profiles") as batch:
        batch.drop_column("wants_kvk_support")
        batch.drop_column("wants_fpo_support")
        batch.drop_column("longitude")
        batch.drop_column("latitude")
