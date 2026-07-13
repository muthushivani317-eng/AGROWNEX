"""farm registration tables (farms, locations, boundaries, media)

Revision ID: 0003_farm_tables
Revises: 0002_auth_profile_tables
Create Date: 2026-07-09

Boundaries are stored as GeoJSON in a JSON column (JSONB on PostgreSQL) — the
PostGIS-compatible interchange format. A native ``geometry`` column can be added
later as an additive migration.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_farm_tables"
down_revision: str | None = "0002_auth_profile_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def _pk() -> sa.Column:
    return sa.Column(
        "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
    )


def _timestamps() -> list[sa.Column]:
    now = sa.func.now()
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
    ]


def _soft_delete() -> list[sa.Column]:
    return [
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    ]


def upgrade() -> None:
    op.create_table(
        "farms",
        _pk(),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("crop", sa.String(80), nullable=True),
        sa.Column("crop_variety", sa.String(120), nullable=True),
        sa.Column("sowing_date", sa.Date(), nullable=True),
        sa.Column("soil_type", sa.String(40), nullable=True),
        sa.Column("irrigation_type", sa.String(40), nullable=True),
        sa.Column("water_source", sa.String(40), nullable=True),
        sa.Column("area_hectares", sa.Float(), nullable=True),
        sa.Column("area_source", sa.String(10), nullable=False, server_default="auto"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        *_timestamps(),
        *_soft_delete(),
    )
    op.create_index("idx_farms_user", "farms", ["user_id"])
    op.create_index("idx_farms_crop", "farms", ["crop"])
    op.create_index("idx_farms_status", "farms", ["status"])

    op.create_table(
        "farm_locations",
        _pk(),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("elevation", sa.Float(), nullable=True),
        sa.Column("address", sa.String(255), nullable=True),
        sa.Column("district", sa.String(80), nullable=True),
        sa.Column("block", sa.String(80), nullable=True),
        sa.Column("village", sa.String(80), nullable=True),
        sa.Column("source", sa.String(10), nullable=False, server_default="gps"),
        *_timestamps(),
    )
    op.create_unique_constraint("uq_farm_locations_farm", "farm_locations", ["farm_id"])
    op.create_index("idx_farm_locations_district", "farm_locations", ["district"])
    op.create_index("idx_farm_locations_block", "farm_locations", ["block"])
    op.create_index("idx_farm_locations_village", "farm_locations", ["village"])

    op.create_table(
        "farm_boundaries",
        _pk(),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=False),
        sa.Column("geojson", sa.JSON(), nullable=True),
        sa.Column("area_hectares", sa.Float(), nullable=True),
        sa.Column("perimeter_m", sa.Float(), nullable=True),
        sa.Column("centroid_lat", sa.Float(), nullable=True),
        sa.Column("centroid_lng", sa.Float(), nullable=True),
        sa.Column("vertex_count", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(10), nullable=False, server_default="drawn"),
        *_timestamps(),
    )
    op.create_unique_constraint(
        "uq_farm_boundaries_farm", "farm_boundaries", ["farm_id"]
    )

    op.create_table(
        "farm_media",
        _pk(),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id"), nullable=False),
        sa.Column("file_url", sa.String(512), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("mime_type", sa.String(80), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("caption", sa.String(255), nullable=True),
        sa.Column("uploaded_by", UUID, sa.ForeignKey("users.id"), nullable=True),
        *_timestamps(),
    )
    op.create_index("idx_farm_media_farm", "farm_media", ["farm_id"])


def downgrade() -> None:
    op.drop_table("farm_media")
    op.drop_table("farm_boundaries")
    op.drop_table("farm_locations")
    op.drop_table("farms")
