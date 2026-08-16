"""add controlled equipment requests

Revision ID: b68ed53d0f2a
Revises: f34c91a127b0
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b68ed53d0f2a"
down_revision = "f34c91a127b0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "equipment_listings",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("owner_user_id", uuid, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("equipment_type", sa.String(40), nullable=False),
        sa.Column("district", sa.String(80)), sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(20), server_default="available", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),  # noqa: E501
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),  # noqa: E501
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    for column in ("owner_user_id", "equipment_type", "district", "status"):
        op.create_index(f"ix_equipment_listings_{column}", "equipment_listings", [column])
    op.create_table(
        "equipment_requests",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("listing_id", uuid, sa.ForeignKey("equipment_listings.id", ondelete="CASCADE"), nullable=False),  # noqa: E501
        sa.Column("requester_user_id", uuid, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", uuid, sa.ForeignKey("farms.id"), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("purpose", sa.String(500)),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("decision_note", sa.String(500)),
        sa.Column("decided_by", uuid, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),  # noqa: E501
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),  # noqa: E501
    )
    for column in ("listing_id", "requester_user_id", "farm_id", "status"):
        op.create_index(f"ix_equipment_requests_{column}", "equipment_requests", [column])


def downgrade() -> None:
    op.drop_table("equipment_requests")
    op.drop_table("equipment_listings")
