"""Organic Inputs Marketplace foundation: catalogue, supplier onboarding, batches.

Revision ID: d3f8a61c9b52
Revises: 6b1d9f4a2c83
"""
from alembic import op
import sqlalchemy as sa

from app.shared.base_model import GUID

revision = "d3f8a61c9b52"
down_revision = "6b1d9f4a2c83"
branch_labels = None
depends_on = None


def _base():
    return [
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def _soft_delete():
    return [
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    ]


def upgrade():
    op.create_table(
        "organic_inputs_categories", *_base(), *_soft_delete(),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("name_ta", sa.String(160)),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("slug", name="uq_organic_inputs_category_slug"),
    )
    op.create_index("ix_organic_inputs_categories_slug", "organic_inputs_categories", ["slug"])
    op.create_index("ix_organic_inputs_categories_status", "organic_inputs_categories", ["status"])

    op.create_table(
        "organic_inputs_product_types", *_base(), *_soft_delete(),
        sa.Column("category_id", GUID(), sa.ForeignKey("organic_inputs_categories.id"), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("name_ta", sa.String(160)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.UniqueConstraint("slug", name="uq_organic_inputs_product_type_slug"),
    )
    op.create_index("ix_organic_inputs_product_types_category_id", "organic_inputs_product_types", ["category_id"])
    op.create_index("ix_organic_inputs_product_types_slug", "organic_inputs_product_types", ["slug"])
    op.create_index("ix_organic_inputs_product_types_status", "organic_inputs_product_types", ["status"])

    op.create_table(
        "organic_inputs_product_type_versions", *_base(),
        sa.Column("product_type_id", GUID(), sa.ForeignKey("organic_inputs_product_types.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("description", sa.Text()),
        sa.Column("description_ta", sa.Text()),
        sa.Column("product_form", sa.String(40)),
        sa.Column("unit_of_measurement", sa.String(32), nullable=False),
        sa.Column("allowed_pack_sizes", sa.JSON(), nullable=False),
        sa.Column("intended_purposes", sa.JSON(), nullable=False),
        sa.Column("suitable_crops", sa.JSON(), nullable=False),
        sa.Column("suitable_crop_stages", sa.JSON(), nullable=False),
        sa.Column("ingredient_schema", sa.JSON(), nullable=False),
        sa.Column("preparation_method_requirements", sa.Text()),
        sa.Column("storage_requirements", sa.Text()),
        sa.Column("testing_requirements", sa.JSON(), nullable=False),
        sa.Column("shelf_life_rules", sa.JSON(), nullable=False),
        sa.Column("regulatory_classification", sa.String(60)),
        sa.Column("required_supplier_documents", sa.JSON(), nullable=False),
        sa.Column("required_product_documents", sa.JSON(), nullable=False),
        sa.Column("allowed_public_claims", sa.JSON(), nullable=False),
        sa.Column("safety_instructions", sa.Text()),
        sa.CheckConstraint("version > 0", name="ck_organic_inputs_ptv_version_positive"),
        sa.UniqueConstraint("product_type_id", "version", name="uq_organic_inputs_ptv_version"),
    )
    op.create_index("ix_organic_inputs_ptv_product_type_id", "organic_inputs_product_type_versions", ["product_type_id"])
    op.create_index("ix_organic_inputs_ptv_is_current", "organic_inputs_product_type_versions", ["is_current"])

    op.create_table(
        "organic_inputs_new_product_requests", *_base(),
        sa.Column("requested_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("category_id", GUID(), sa.ForeignKey("organic_inputs_categories.id")),
        sa.Column("proposed_name_en", sa.String(160), nullable=False),
        sa.Column("proposed_name_ta", sa.String(160)),
        sa.Column("description", sa.Text()),
        sa.Column("ingredients", sa.Text()),
        sa.Column("preparation_process", sa.Text()),
        sa.Column("intended_use", sa.Text()),
        sa.Column("photo_urls", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("reviewed_by_admin_id", GUID(), sa.ForeignKey("admin_users.id")),
        sa.Column("review_note", sa.Text()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("resulting_product_type_id", GUID(), sa.ForeignKey("organic_inputs_product_types.id")),
    )
    op.create_index("ix_organic_inputs_npr_requested_by", "organic_inputs_new_product_requests", ["requested_by_user_id"])
    op.create_index("ix_organic_inputs_npr_status", "organic_inputs_new_product_requests", ["status"])

    op.create_table(
        "organic_inputs_supplier_profiles", *_base(),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("farm_id", GUID(), sa.ForeignKey("farms.id")),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("production_location", sa.String(255)),
        sa.Column("district", sa.String(80)),
        sa.Column("village", sa.String(80)),
        sa.Column("contact_name", sa.String(160)),
        sa.Column("contact_phone", sa.String(20)),
        sa.Column("production_capacity_note", sa.Text()),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("reviewed_by_admin_id", GUID(), sa.ForeignKey("admin_users.id")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("rejection_reason", sa.Text()),
        sa.Column("suspension_reason", sa.Text()),
        sa.UniqueConstraint("user_id", name="uq_organic_inputs_supplier_user"),
    )
    op.create_index("ix_organic_inputs_supplier_user_id", "organic_inputs_supplier_profiles", ["user_id"])
    op.create_index("ix_organic_inputs_supplier_status", "organic_inputs_supplier_profiles", ["status"])

    op.create_table(
        "organic_inputs_supplier_documents", *_base(),
        sa.Column("supplier_id", GUID(), sa.ForeignKey("organic_inputs_supplier_profiles.id"), nullable=False),
        sa.Column("document_type", sa.String(40), nullable=False),
        sa.Column("file_url", sa.String(512), nullable=False),
        sa.Column("file_name", sa.String(255)),
        sa.Column("mime_type", sa.String(80)),
        sa.Column("file_size", sa.Integer()),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("verification_note", sa.Text()),
    )
    op.create_index("ix_organic_inputs_supplier_doc_supplier_id", "organic_inputs_supplier_documents", ["supplier_id"])

    op.create_table(
        "organic_inputs_production_batches", *_base(), *_soft_delete(),
        sa.Column("batch_code", sa.String(24), nullable=False),
        sa.Column("supplier_id", GUID(), sa.ForeignKey("organic_inputs_supplier_profiles.id"), nullable=False),
        sa.Column("product_type_id", GUID(), sa.ForeignKey("organic_inputs_product_types.id"), nullable=False),
        sa.Column("product_type_version_id", GUID(), sa.ForeignKey("organic_inputs_product_type_versions.id"), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("production_location", sa.String(255)),
        sa.Column("production_start_date", sa.Date()),
        sa.Column("production_completion_date", sa.Date()),
        sa.Column("preparation_method", sa.Text()),
        sa.Column("batch_quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.Column("available_quantity_offered", sa.Numeric(14, 3)),
        sa.Column("expected_procurement_price", sa.Numeric(14, 2)),
        sa.Column("storage_method", sa.Text()),
        sa.Column("use_before_date", sa.Date()),
        sa.Column("submission_date", sa.DateTime(timezone=True)),
        sa.Column("latest_review_note", sa.Text()),
        sa.Column("approved_quantity", sa.Numeric(14, 3)),
        sa.Column("rejected_quantity", sa.Numeric(14, 3)),
        sa.CheckConstraint("batch_quantity > 0", name="ck_organic_inputs_batch_quantity_positive"),
        sa.CheckConstraint(
            "available_quantity_offered IS NULL OR available_quantity_offered > 0",
            name="ck_organic_inputs_batch_offered_positive",
        ),
        sa.CheckConstraint(
            "expected_procurement_price IS NULL OR expected_procurement_price > 0",
            name="ck_organic_inputs_batch_price_positive",
        ),
        sa.UniqueConstraint("batch_code", name="uq_organic_inputs_batch_code"),
    )
    op.create_index("ix_organic_inputs_batch_code", "organic_inputs_production_batches", ["batch_code"])
    op.create_index("ix_organic_inputs_batch_supplier_id", "organic_inputs_production_batches", ["supplier_id"])
    op.create_index("ix_organic_inputs_batch_product_type_id", "organic_inputs_production_batches", ["product_type_id"])
    op.create_index("ix_organic_inputs_batch_status", "organic_inputs_production_batches", ["status"])

    op.create_table(
        "organic_inputs_batch_ingredients", *_base(),
        sa.Column("batch_id", GUID(), sa.ForeignKey("organic_inputs_production_batches.id"), nullable=False),
        sa.Column("ingredient_name", sa.String(160), nullable=False),
        sa.Column("ingredient_name_ta", sa.String(160)),
        sa.Column("source", sa.String(255)),
        sa.Column("quantity", sa.Numeric(14, 3)),
        sa.Column("unit", sa.String(32)),
        sa.Column("notes", sa.Text()),
    )
    op.create_index("ix_organic_inputs_batch_ingredient_batch_id", "organic_inputs_batch_ingredients", ["batch_id"])

    op.create_table(
        "organic_inputs_batch_documents", *_base(),
        sa.Column("batch_id", GUID(), sa.ForeignKey("organic_inputs_production_batches.id"), nullable=False),
        sa.Column("document_type", sa.String(40), nullable=False),
        sa.Column("file_url", sa.String(512), nullable=False),
        sa.Column("file_name", sa.String(255)),
        sa.Column("mime_type", sa.String(80)),
        sa.Column("file_size", sa.Integer()),
        sa.Column("caption", sa.String(255)),
    )
    op.create_index("ix_organic_inputs_batch_document_batch_id", "organic_inputs_batch_documents", ["batch_id"])


def downgrade():
    op.drop_table("organic_inputs_batch_documents")
    op.drop_table("organic_inputs_batch_ingredients")
    op.drop_table("organic_inputs_production_batches")
    op.drop_table("organic_inputs_supplier_documents")
    op.drop_table("organic_inputs_supplier_profiles")
    op.drop_table("organic_inputs_new_product_requests")
    op.drop_table("organic_inputs_product_type_versions")
    op.drop_table("organic_inputs_product_types")
    op.drop_table("organic_inputs_categories")
