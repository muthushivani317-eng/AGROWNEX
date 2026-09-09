"""add organic farm profile, protected certificates and governed input library

Revision ID: e4b7c2d91a60
Revises: 1ae3bce50f2a
"""

import sqlalchemy as sa
from alembic import op
from app.shared.base_model import GUID

revision = "e4b7c2d91a60"
down_revision = "1ae3bce50f2a"
branch_labels = None
depends_on = None


def _timestamps():
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "organic_farm_profiles",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column(
            "farm_id",
            GUID(),
            sa.ForeignKey("farms.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("mode", sa.String(32), nullable=False, server_default="conventional"),
        sa.Column("transition_start_date", sa.Date()),
        sa.Column("goals", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("preferred_practices", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("avoided_input_categories", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column(
            "certification_status", sa.String(32), nullable=False, server_default="not_claimed"
        ),
        sa.Column("certification_scheme", sa.String(120)),
        sa.Column("certification_identifier", sa.String(160)),
        sa.Column("certificate_issued_on", sa.Date()),
        sa.Column("certificate_expires_on", sa.Date()),
        sa.Column("certification_verified_at", sa.DateTime(timezone=True)),
        sa.Column(
            "certification_verified_by", GUID(), sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        sa.Column("plan_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("last_idempotency_key", sa.String(128)),
        *_timestamps(),
    )
    op.create_index("ix_organic_farm_profiles_farm_id", "organic_farm_profiles", ["farm_id"])
    op.create_index(
        "ix_organic_farm_profiles_certification_status",
        "organic_farm_profiles",
        ["certification_status"],
    )
    op.create_table(
        "organic_certification_documents",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column(
            "profile_id",
            GUID(),
            sa.ForeignKey("organic_farm_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "uploaded_by", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("object_key", sa.String(512), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column(
            "review_status", sa.String(32), nullable=False, server_default="document_submitted"
        ),
        *_timestamps(),
        sa.UniqueConstraint(
            "profile_id", "idempotency_key", name="uq_organic_cert_document_idempotency"
        ),
    )
    op.create_index(
        "ix_organic_certification_documents_profile_id",
        "organic_certification_documents",
        ["profile_id"],
    )
    op.create_table(
        "organic_inputs",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("name_en", sa.String(180), nullable=False),
        sa.Column("name_ta", sa.String(180), nullable=False),
        sa.Column("purpose_en", sa.Text(), nullable=False),
        sa.Column("purpose_ta", sa.Text(), nullable=False),
        sa.Column("guidance", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("applicable_crops", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("applicable_stages", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("applicable_regions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("limitations", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("source_organization", sa.String(180), nullable=False),
        sa.Column("document_reference", sa.String(255), nullable=False),
        sa.Column("source_url", sa.String(512), nullable=False),
        sa.Column("source_version", sa.String(80), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("review_status", sa.String(24), nullable=False, server_default="draft"),
        sa.Column("reviewed_by", GUID(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("effective_from", sa.Date()),
        sa.Column("review_due_on", sa.Date()),
        *_timestamps(),
        sa.UniqueConstraint("slug", "source_version", name="uq_organic_input_slug_version"),
    )
    op.create_index("ix_organic_inputs_slug", "organic_inputs", ["slug"])
    op.create_index("ix_organic_inputs_category", "organic_inputs", ["category"])
    op.create_index("ix_organic_inputs_review_status", "organic_inputs", ["review_status"])


def downgrade() -> None:
    op.drop_table("organic_inputs")
    op.drop_table("organic_certification_documents")
    op.drop_table("organic_farm_profiles")
