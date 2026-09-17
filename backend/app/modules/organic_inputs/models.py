"""Organic Inputs Marketplace ORM models — foundation phase.

Dynamic catalogue (category → product type → versioned definition), supplier
onboarding, and production batches. Procurement, inventory, cart/orders and
traceability are later phases and have no tables here yet (docs:
AGROWAI_ORGANIC_INPUTS_MARKETPLACE).

Money is not modelled in this phase (no procurement offers yet); wherever a
future phase adds it, use ``Numeric`` fixed-precision columns, never floats --
see ``ProductionBatch.expected_procurement_price`` for the convention.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.organic_inputs.constants import (
    BatchStatus,
    CatalogStatus,
    NewProductRequestStatus,
    SupplierStatus,
)
from app.shared.base_model import GUID, Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class MarketplaceCategory(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Admin-managed top-level category (e.g. "Liquid organic inputs")."""

    __tablename__ = "organic_inputs_categories"
    __table_args__ = (UniqueConstraint("slug", name="uq_organic_inputs_category_slug"),)

    slug: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    name_ta: Mapped[str | None] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=CatalogStatus.ACTIVE.value, index=True
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class MarketplaceProductType(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A product type within a category (e.g. "Fish amino acid").

    The actual admin-configurable definition (units, pack sizes, testing
    requirements, claims, etc.) lives on :class:`ProductTypeVersion` --
    editing it creates a new version rather than mutating history that live
    batches/products may already reference.
    """

    __tablename__ = "organic_inputs_product_types"
    __table_args__ = (UniqueConstraint("slug", name="uq_organic_inputs_product_type_slug"),)

    category_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organic_inputs_categories.id"), nullable=False, index=True
    )
    slug: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    name_ta: Mapped[str | None] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=CatalogStatus.DRAFT.value, index=True
    )

    versions: Mapped[list[ProductTypeVersion]] = relationship(
        back_populates="product_type", lazy="selectin", order_by="ProductTypeVersion.version"
    )


class ProductTypeVersion(UUIDMixin, TimestampMixin, Base):
    """One admin-authored, versioned definition of a product type.

    Everything an admin needs to configure per product type without a code
    change lives here as data (docs section 2): units, pack sizes, purposes,
    suitable crops/stages, ingredient schema, storage/testing/shelf-life
    rules, regulatory classification, required documents, allowed public
    claims and safety instructions. Structured, per-parameter test limits and
    normalized document/compliance requirement tables are QC-phase additions;
    for now these are admin-editable JSON so the catalogue stays dynamic
    without a schema migration for every new requirement shape.
    """

    __tablename__ = "organic_inputs_product_type_versions"
    __table_args__ = (
        UniqueConstraint("product_type_id", "version", name="uq_organic_inputs_ptv_version"),
        CheckConstraint("version > 0", name="ck_organic_inputs_ptv_version_positive"),
    )

    product_type_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organic_inputs_product_types.id"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    description: Mapped[str | None] = mapped_column(Text)
    description_ta: Mapped[str | None] = mapped_column(Text)
    product_form: Mapped[str | None] = mapped_column(String(40))  # liquid/powder/cake/etc.
    unit_of_measurement: Mapped[str] = mapped_column(String(32), nullable=False)
    allowed_pack_sizes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    intended_purposes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    suitable_crops: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    suitable_crop_stages: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    ingredient_schema: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    preparation_method_requirements: Mapped[str | None] = mapped_column(Text)
    storage_requirements: Mapped[str | None] = mapped_column(Text)
    testing_requirements: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    shelf_life_rules: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    regulatory_classification: Mapped[str | None] = mapped_column(String(60))
    required_supplier_documents: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    required_product_documents: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    allowed_public_claims: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    safety_instructions: Mapped[str | None] = mapped_column(Text)

    product_type: Mapped[MarketplaceProductType] = relationship(back_populates="versions")


class NewProductTypeRequest(UUIDMixin, TimestampMixin, Base):
    """A farmer's request for a product type not yet in the catalogue.

    Never publicly visible and never itself sellable (docs section 2) --
    approval only opens an admin-review queue entry; an admin still has to
    create the real :class:`MarketplaceProductType` deliberately.
    """

    __tablename__ = "organic_inputs_new_product_requests"

    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=False, index=True
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("organic_inputs_categories.id")
    )
    proposed_name_en: Mapped[str] = mapped_column(String(160), nullable=False)
    proposed_name_ta: Mapped[str | None] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    ingredients: Mapped[str | None] = mapped_column(Text)
    preparation_process: Mapped[str | None] = mapped_column(Text)
    intended_use: Mapped[str | None] = mapped_column(Text)
    photo_urls: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=NewProductRequestStatus.PENDING.value, index=True
    )
    reviewed_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("admin_users.id")
    )
    review_note: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resulting_product_type_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("organic_inputs_product_types.id")
    )


class SupplierProfile(UUIDMixin, TimestampMixin, Base):
    """A farmer's application/approval to sell organic inputs to AgrowAI.

    One profile per farmer. Per-product-type approval granularity
    (``SupplierProductApproval`` in the full spec) is deferred to the QC
    phase alongside inspection/testing -- an APPROVED supplier here may
    submit a batch for any ACTIVE product type until that lands. Bank/UPI
    payout details are intentionally NOT captured yet: this repo has no
    existing field-level-encryption utility, and inventing one ad hoc for a
    payout column is a security decision that belongs with the procurement
    phase that actually needs it, not smuggled in here.
    """

    __tablename__ = "organic_inputs_supplier_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_organic_inputs_supplier_user"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=False, index=True
    )
    farm_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("farms.id"))
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default=SupplierStatus.DRAFT.value, index=True
    )
    production_location: Mapped[str | None] = mapped_column(String(255))
    district: Mapped[str | None] = mapped_column(String(80))
    village: Mapped[str | None] = mapped_column(String(80))
    contact_name: Mapped[str | None] = mapped_column(String(160))
    contact_phone: Mapped[str | None] = mapped_column(String(20))
    production_capacity_note: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("admin_users.id")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    suspension_reason: Mapped[str | None] = mapped_column(Text)

    documents: Mapped[list[SupplierDocument]] = relationship(
        back_populates="supplier", lazy="selectin", cascade="all, delete-orphan"
    )


class SupplierDocument(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organic_inputs_supplier_documents"

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organic_inputs_supplier_profiles.id"), nullable=False, index=True
    )
    document_type: Mapped[str] = mapped_column(String(40), nullable=False)
    file_url: Mapped[str] = mapped_column(String(512), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str | None] = mapped_column(String(80))
    file_size: Mapped[int | None] = mapped_column(Integer)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification_note: Mapped[str | None] = mapped_column(Text)

    supplier: Mapped[SupplierProfile] = relationship(back_populates="documents")


class ProductionBatch(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A supplier's production batch offered to AgrowAI.

    Inspection results, sample records and lab test results are separate
    tables the QC phase adds (docs section 17 lists them as their own
    entities, not batch columns) -- this model deliberately stops at what the
    farmer themselves declares plus the review/decision trail.
    """

    __tablename__ = "organic_inputs_production_batches"
    __table_args__ = (
        UniqueConstraint("batch_code", name="uq_organic_inputs_batch_code"),
        CheckConstraint("batch_quantity > 0", name="ck_organic_inputs_batch_quantity_positive"),
        CheckConstraint(
            "available_quantity_offered IS NULL OR available_quantity_offered > 0",
            name="ck_organic_inputs_batch_offered_positive",
        ),
        CheckConstraint(
            "expected_procurement_price IS NULL OR expected_procurement_price > 0",
            name="ck_organic_inputs_batch_price_positive",
        ),
    )

    batch_code: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organic_inputs_supplier_profiles.id"), nullable=False, index=True
    )
    product_type_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organic_inputs_product_types.id"), nullable=False, index=True
    )
    product_type_version_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organic_inputs_product_type_versions.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default=BatchStatus.DRAFT.value, index=True
    )
    production_location: Mapped[str | None] = mapped_column(String(255))
    production_start_date: Mapped[date | None] = mapped_column(Date)
    production_completion_date: Mapped[date | None] = mapped_column(Date)
    preparation_method: Mapped[str | None] = mapped_column(Text)
    batch_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    available_quantity_offered: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    expected_procurement_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    storage_method: Mapped[str | None] = mapped_column(Text)
    use_before_date: Mapped[date | None] = mapped_column(Date)
    submission_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latest_review_note: Mapped[str | None] = mapped_column(Text)
    approved_quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    rejected_quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))

    ingredients: Mapped[list[BatchIngredient]] = relationship(
        back_populates="batch", lazy="selectin", cascade="all, delete-orphan"
    )
    documents: Mapped[list[BatchDocument]] = relationship(
        back_populates="batch", lazy="selectin", cascade="all, delete-orphan"
    )


class BatchIngredient(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organic_inputs_batch_ingredients"

    batch_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organic_inputs_production_batches.id"), nullable=False, index=True
    )
    ingredient_name: Mapped[str] = mapped_column(String(160), nullable=False)
    ingredient_name_ta: Mapped[str | None] = mapped_column(String(160))
    source: Mapped[str | None] = mapped_column(String(255))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    unit: Mapped[str | None] = mapped_column(String(32))
    notes: Mapped[str | None] = mapped_column(Text)

    batch: Mapped[ProductionBatch] = relationship(back_populates="ingredients")


class BatchDocument(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organic_inputs_batch_documents"

    batch_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organic_inputs_production_batches.id"), nullable=False, index=True
    )
    document_type: Mapped[str] = mapped_column(String(40), nullable=False)
    file_url: Mapped[str] = mapped_column(String(512), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str | None] = mapped_column(String(80))
    file_size: Mapped[int | None] = mapped_column(Integer)
    caption: Mapped[str | None] = mapped_column(String(255))

    batch: Mapped[ProductionBatch] = relationship(back_populates="documents")


class BatchInspection(UUIDMixin, TimestampMixin, Base):
    """A physical/site inspection outcome for one batch (QC phase).

    The batch state machine only allows one inspection per batch under the
    current transitions (there's no path back to INSPECTION_REQUIRED once
    left) -- modelled as a table rather than columns on ProductionBatch so a
    correction/re-inspection is possible later without another migration.
    Supporting photos reuse BatchDocument (document_type="inspection_photo")
    rather than a new column here -- see BATCH_DOCUMENT_TYPES.
    """

    __tablename__ = "organic_inputs_batch_inspections"
    __table_args__ = (
        CheckConstraint("outcome IN ('passed', 'failed')", name="ck_organic_inputs_inspection_outcome"),
    )

    batch_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organic_inputs_production_batches.id"), nullable=False, index=True
    )
    inspector_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("admin_users.id")
    )
    inspected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    findings_note: Mapped[str | None] = mapped_column(Text)


class BatchSample(UUIDMixin, TimestampMixin, Base):
    """A physical sample drawn from a batch for lab testing (QC phase).

    One-to-many with ProductionBatch: a RETEST_REQUIRED outcome collects a
    fresh sample rather than reusing the old one, preserving the chain of
    custody for each attempt.
    """

    __tablename__ = "organic_inputs_batch_samples"
    __table_args__ = (UniqueConstraint("sample_code", name="uq_organic_inputs_sample_code"),)

    batch_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organic_inputs_production_batches.id"), nullable=False, index=True
    )
    sample_code: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    collected_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("admin_users.id")
    )
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))
    unit: Mapped[str | None] = mapped_column(String(32))
    storage_condition: Mapped[str | None] = mapped_column(Text)
    chain_of_custody_note: Mapped[str | None] = mapped_column(Text)

    test_results: Mapped[list[BatchTestResult]] = relationship(
        back_populates="sample", lazy="selectin", cascade="all, delete-orphan"
    )


class BatchTestResult(UUIDMixin, TimestampMixin, Base):
    """One lab-tested parameter result for a sample (QC phase).

    ``pass_fail`` is entered directly by the Quality Control admin, never
    auto-derived from ``measured_value``/``expected_limit`` -- this repo has
    no test-limit comparison engine, and inventing pass/fail logic ad hoc
    here would be exactly the kind of assumption the spec asked not to make.
    ``expected_limit`` is a snapshot (copied in at test-entry time from
    ``ProductTypeVersion.testing_requirements``) so a later catalogue edit
    never rewrites a historical test record.
    """

    __tablename__ = "organic_inputs_batch_test_results"

    sample_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organic_inputs_batch_samples.id"), nullable=False, index=True
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organic_inputs_production_batches.id"), nullable=False, index=True
    )
    parameter_name: Mapped[str] = mapped_column(String(120), nullable=False)
    parameter_name_ta: Mapped[str | None] = mapped_column(String(120))
    expected_limit: Mapped[dict | None] = mapped_column(JSON)
    measured_value: Mapped[str | None] = mapped_column(String(120))
    unit: Mapped[str | None] = mapped_column(String(32))
    pass_fail: Mapped[bool] = mapped_column(Boolean, nullable=False)
    lab_name: Mapped[str | None] = mapped_column(String(160))
    tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    entered_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("admin_users.id")
    )
    notes: Mapped[str | None] = mapped_column(Text)

    sample: Mapped[BatchSample] = relationship(back_populates="test_results")
