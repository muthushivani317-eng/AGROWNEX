"""add organic upload attestations

Revision ID: d4f8b61e2c90
Revises: c2e7a49d8b31
"""

import sqlalchemy as sa
from alembic import op

revision = "d4f8b61e2c90"
down_revision = "c2e7a49d8b31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organic_upload_attestations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("farm_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(40), nullable=False),
        sa.Column("object_key", sa.String(512), nullable=False),
        sa.Column("object_version", sa.String(64), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_key"),
        sa.UniqueConstraint("object_version"),
    )
    op.create_index(
        "ix_organic_upload_attestations_user_id", "organic_upload_attestations", ["user_id"]
    )
    op.create_index(
        "ix_organic_upload_attestations_farm_id", "organic_upload_attestations", ["farm_id"]
    )
    op.add_column("organic_certification_documents", sa.Column("upload_attestation_id", sa.Uuid()))
    op.create_foreign_key(
        "fk_organic_cert_doc_attestation",
        "organic_certification_documents",
        "organic_upload_attestations",
        ["upload_attestation_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_organic_cert_doc_attestation",
        "organic_certification_documents",
        ["upload_attestation_id"],
    )
    op.add_column("organic_practice_evidence", sa.Column("upload_attestation_id", sa.Uuid()))
    op.create_foreign_key(
        "fk_organic_evidence_attestation",
        "organic_practice_evidence",
        "organic_upload_attestations",
        ["upload_attestation_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_organic_evidence_attestation", "organic_practice_evidence", ["upload_attestation_id"]
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_organic_evidence_attestation", "organic_practice_evidence", type_="unique"
    )
    op.drop_constraint(
        "fk_organic_evidence_attestation", "organic_practice_evidence", type_="foreignkey"
    )
    op.drop_column("organic_practice_evidence", "upload_attestation_id")
    op.drop_constraint(
        "uq_organic_cert_doc_attestation", "organic_certification_documents", type_="unique"
    )
    op.drop_constraint(
        "fk_organic_cert_doc_attestation", "organic_certification_documents", type_="foreignkey"
    )
    op.drop_column("organic_certification_documents", "upload_attestation_id")
    op.drop_index(
        "ix_organic_upload_attestations_farm_id", table_name="organic_upload_attestations"
    )
    op.drop_index(
        "ix_organic_upload_attestations_user_id", table_name="organic_upload_attestations"
    )
    op.drop_table("organic_upload_attestations")
