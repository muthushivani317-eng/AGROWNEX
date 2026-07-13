"""hot-path composite indexes (Phase 3 — scalability)

Adds (user_id, created_at) composite indexes on the highest-traffic
farmer-scoped, time-ordered read paths (disease reports, chats, notifications)
and a (latitude, longitude) index on farm locations.

Note: farm geometry is stored as GeoJSON in a JSON column (not PostGIS
geometry), so a true GiST spatial index does not apply; the lat/long composite
is the correct index for the coordinate lookups the app actually performs.

Revision ID: 0020_hot_path_indexes
Revises: 0019_token_usage
Create Date: 2026-07-13
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0020_hot_path_indexes"
down_revision: str | None = "0019_token_usage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "idx_disease_reports_user_created",
        "disease_reports",
        ["user_id", "created_at"],
    )
    op.create_index(
        "idx_ai_conversations_user_created",
        "ai_conversations",
        ["user_id", "created_at"],
    )
    op.create_index(
        "idx_notifications_user_created",
        "notifications",
        ["user_id", "created_at"],
    )
    op.create_index(
        "idx_farm_locations_lat_lng",
        "farm_locations",
        ["latitude", "longitude"],
    )


def downgrade() -> None:
    op.drop_index("idx_farm_locations_lat_lng", table_name="farm_locations")
    op.drop_index("idx_notifications_user_created", table_name="notifications")
    op.drop_index("idx_ai_conversations_user_created", table_name="ai_conversations")
    op.drop_index("idx_disease_reports_user_created", table_name="disease_reports")
