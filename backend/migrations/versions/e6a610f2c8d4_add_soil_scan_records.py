"""add immutable soil scan records

Revision ID: e6a610f2c8d4
Revises: d628f4a72c10
"""

import sqlalchemy as sa
from alembic import op
from app.shared.base_model import GUID

revision = "e6a610f2c8d4"
down_revision = "d628f4a72c10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "soil_scan_records",
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("farm_id", GUID(), nullable=False),
        sa.Column("aoi_geojson", sa.JSON(), nullable=True),
        sa.Column("aoi_reference", sa.String(length=80), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider_states", sa.JSON(), nullable=False),
        sa.Column("indicators", sa.JSON(), nullable=False),
        sa.Column("sampling_plan", sa.JSON(), nullable=True),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_soil_scan_records_user_id", "soil_scan_records", ["user_id"])
    op.create_index("ix_soil_scan_records_farm_id", "soil_scan_records", ["farm_id"])
    op.create_index("ix_soil_scan_records_generated_at", "soil_scan_records", ["generated_at"])


def downgrade() -> None:
    op.drop_index("ix_soil_scan_records_generated_at", table_name="soil_scan_records")
    op.drop_index("ix_soil_scan_records_farm_id", table_name="soil_scan_records")
    op.drop_index("ix_soil_scan_records_user_id", table_name="soil_scan_records")
    op.drop_table("soil_scan_records")
