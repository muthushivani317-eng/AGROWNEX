"""Partner API keys for the external FPO/organization data feed.

Revision ID: 6b1d9f4a2c83
Revises: a4d8f21b6c90
"""
from alembic import op
import sqlalchemy as sa

from app.shared.base_model import GUID

revision = "6b1d9f4a2c83"
down_revision = "a4d8f21b6c90"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "organic_partner_api_keys",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("organization_id", GUID(), sa.ForeignKey("organic_partner_organizations.id"), nullable=False),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("key_prefix", sa.String(16), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("key_prefix", name="uq_organic_partner_api_key_prefix"),
    )
    op.create_index(
        "ix_organic_partner_api_keys_organization_id",
        "organic_partner_api_keys",
        ["organization_id"],
    )
    op.create_index(
        "ix_organic_partner_api_keys_key_prefix",
        "organic_partner_api_keys",
        ["key_prefix"],
    )


def downgrade():
    op.drop_table("organic_partner_api_keys")
