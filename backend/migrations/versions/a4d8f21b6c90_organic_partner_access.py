"""Scoped organic partner organizations, staff and farmer links.

Revision ID: a4d8f21b6c90
Revises: c9f412a7e60b
"""
from alembic import op
import sqlalchemy as sa

from app.shared.base_model import GUID

revision = "a4d8f21b6c90"
down_revision = "c9f412a7e60b"
branch_labels = None
depends_on = None


def _base():
    return [
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade():
    op.create_table("organic_partner_organizations", *_base(),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("fpo_id", GUID(), sa.ForeignKey("organic_fpos.id"), unique=True),
        sa.Column("is_test", sa.Boolean(), nullable=False))
    op.create_table("organic_partner_staff", *_base(),
        sa.Column("organization_id", GUID(), sa.ForeignKey("organic_partner_organizations.id"), nullable=False),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(24), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_organic_partner_staff"))
    op.create_table("organic_partner_farmer_links", *_base(),
        sa.Column("organization_id", GUID(), sa.ForeignKey("organic_partner_organizations.id"), nullable=False),
        sa.Column("farmer_user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("requested_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("organization_id", "farmer_user_id", name="uq_organic_partner_farmer"))
    for table, column in (("organic_partner_staff", "organization_id"),
                          ("organic_partner_staff", "user_id"),
                          ("organic_partner_farmer_links", "organization_id"),
                          ("organic_partner_farmer_links", "farmer_user_id")):
        op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade():
    op.drop_table("organic_partner_farmer_links")
    op.drop_table("organic_partner_staff")
    op.drop_table("organic_partner_organizations")
