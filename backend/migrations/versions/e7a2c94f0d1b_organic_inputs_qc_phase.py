"""Organic Inputs Marketplace QC phase: inspection, sampling, lab test results.

Revision ID: e7a2c94f0d1b
Revises: d3f8a61c9b52
"""
from alembic import op
import sqlalchemy as sa

from app.shared.base_model import GUID

revision = "e7a2c94f0d1b"
down_revision = "d3f8a61c9b52"
branch_labels = None
depends_on = None


def _base():
    return [
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade():
    op.create_table(
        "organic_inputs_batch_inspections", *_base(),
        sa.Column("batch_id", GUID(), sa.ForeignKey("organic_inputs_production_batches.id"), nullable=False),
        sa.Column("inspector_admin_id", GUID(), sa.ForeignKey("admin_users.id")),
        sa.Column("inspected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("findings_note", sa.Text()),
        sa.CheckConstraint("outcome IN ('passed', 'failed')", name="ck_organic_inputs_inspection_outcome"),
    )
    op.create_index(
        "ix_organic_inputs_inspection_batch_id", "organic_inputs_batch_inspections", ["batch_id"]
    )

    op.create_table(
        "organic_inputs_batch_samples", *_base(),
        sa.Column("batch_id", GUID(), sa.ForeignKey("organic_inputs_production_batches.id"), nullable=False),
        sa.Column("sample_code", sa.String(24), nullable=False),
        sa.Column("collected_by_admin_id", GUID(), sa.ForeignKey("admin_users.id")),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3)),
        sa.Column("unit", sa.String(32)),
        sa.Column("storage_condition", sa.Text()),
        sa.Column("chain_of_custody_note", sa.Text()),
        sa.UniqueConstraint("sample_code", name="uq_organic_inputs_sample_code"),
    )
    op.create_index("ix_organic_inputs_sample_batch_id", "organic_inputs_batch_samples", ["batch_id"])
    op.create_index("ix_organic_inputs_sample_code", "organic_inputs_batch_samples", ["sample_code"])

    op.create_table(
        "organic_inputs_batch_test_results", *_base(),
        sa.Column("sample_id", GUID(), sa.ForeignKey("organic_inputs_batch_samples.id"), nullable=False),
        sa.Column("batch_id", GUID(), sa.ForeignKey("organic_inputs_production_batches.id"), nullable=False),
        sa.Column("parameter_name", sa.String(120), nullable=False),
        sa.Column("parameter_name_ta", sa.String(120)),
        sa.Column("expected_limit", sa.JSON()),
        sa.Column("measured_value", sa.String(120)),
        sa.Column("unit", sa.String(32)),
        sa.Column("pass_fail", sa.Boolean(), nullable=False),
        sa.Column("lab_name", sa.String(160)),
        sa.Column("tested_at", sa.DateTime(timezone=True)),
        sa.Column("entered_by_admin_id", GUID(), sa.ForeignKey("admin_users.id")),
        sa.Column("notes", sa.Text()),
    )
    op.create_index(
        "ix_organic_inputs_test_result_sample_id", "organic_inputs_batch_test_results", ["sample_id"]
    )
    op.create_index(
        "ix_organic_inputs_test_result_batch_id", "organic_inputs_batch_test_results", ["batch_id"]
    )


def downgrade():
    op.drop_table("organic_inputs_batch_test_results")
    op.drop_table("organic_inputs_batch_samples")
    op.drop_table("organic_inputs_batch_inspections")
