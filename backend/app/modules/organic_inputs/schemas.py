"""Organic Inputs Marketplace request/response schemas — foundation phase."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.organic_inputs.constants import (
    BatchStatus,
    CatalogStatus,
    NewProductRequestStatus,
    SupplierStatus,
)
from app.shared.url_safety import HttpsUrl

# ---------------------------------------------------------------------------
# Catalogue (admin write / public read)
# ---------------------------------------------------------------------------


class CategoryIn(BaseModel):
    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=2, max_length=160)
    name_ta: str | None = Field(default=None, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    display_order: int = 0


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    slug: str
    name: str
    name_ta: str | None
    description: str | None
    status: str
    display_order: int


class ProductTypeIn(BaseModel):
    category_id: uuid.UUID
    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=2, max_length=160)
    name_ta: str | None = Field(default=None, max_length=160)


class ProductTypeVersionIn(BaseModel):
    """The admin-editable definition for a product type (docs section 2).

    Submitting this creates a NEW version and marks it current -- it never
    mutates a version a live batch may already reference.
    """

    description: str | None = Field(default=None, max_length=4000)
    description_ta: str | None = Field(default=None, max_length=4000)
    product_form: str | None = Field(default=None, max_length=40)
    unit_of_measurement: str = Field(min_length=1, max_length=32)
    allowed_pack_sizes: list[str] = Field(default_factory=list, max_length=30)
    intended_purposes: list[str] = Field(default_factory=list, max_length=30)
    suitable_crops: list[str] = Field(default_factory=list, max_length=100)
    suitable_crop_stages: list[str] = Field(default_factory=list, max_length=30)
    ingredient_schema: dict = Field(default_factory=dict)
    preparation_method_requirements: str | None = Field(default=None, max_length=4000)
    storage_requirements: str | None = Field(default=None, max_length=2000)
    testing_requirements: dict = Field(default_factory=dict)
    shelf_life_rules: dict = Field(default_factory=dict)
    regulatory_classification: str | None = Field(default=None, max_length=60)
    required_supplier_documents: list[str] = Field(default_factory=list, max_length=30)
    required_product_documents: list[str] = Field(default_factory=list, max_length=30)
    allowed_public_claims: list[str] = Field(default_factory=list, max_length=30)
    safety_instructions: str | None = Field(default=None, max_length=4000)


class ProductTypeVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    version: int
    is_current: bool
    unit_of_measurement: str
    allowed_pack_sizes: list
    intended_purposes: list
    suitable_crops: list
    suitable_crop_stages: list
    regulatory_classification: str | None
    updated_at: datetime


class ProductTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    category_id: uuid.UUID
    slug: str
    name: str
    name_ta: str | None
    status: str
    current_version: ProductTypeVersionOut | None = None


class CatalogStatusIn(BaseModel):
    status: CatalogStatus


class NewProductTypeRequestIn(BaseModel):
    category_id: uuid.UUID | None = None
    proposed_name_en: str = Field(min_length=2, max_length=160)
    proposed_name_ta: str | None = Field(default=None, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    ingredients: str | None = Field(default=None, max_length=4000)
    preparation_process: str | None = Field(default=None, max_length=4000)
    intended_use: str | None = Field(default=None, max_length=2000)
    photo_urls: list[HttpsUrl] = Field(default_factory=list, max_length=10)


class NewProductTypeRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    proposed_name_en: str
    proposed_name_ta: str | None
    status: str
    review_note: str | None
    created_at: datetime


class NewProductTypeRequestDecisionIn(BaseModel):
    status: NewProductRequestStatus
    review_note: str | None = Field(default=None, max_length=2000)


# ---------------------------------------------------------------------------
# Supplier onboarding
# ---------------------------------------------------------------------------


class SupplierApplyIn(BaseModel):
    farm_id: uuid.UUID | None = None
    production_location: str | None = Field(default=None, max_length=255)
    district: str | None = Field(default=None, max_length=80)
    village: str | None = Field(default=None, max_length=80)
    contact_name: str | None = Field(default=None, max_length=160)
    contact_phone: str | None = Field(default=None, max_length=20)
    production_capacity_note: str | None = Field(default=None, max_length=2000)


class SupplierProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    status: str
    production_location: str | None
    district: str | None
    village: str | None
    contact_name: str | None
    contact_phone: str | None
    production_capacity_note: str | None
    rejection_reason: str | None
    suspension_reason: str | None
    created_at: datetime
    updated_at: datetime


class SupplierDocumentIn(BaseModel):
    document_type: str = Field(min_length=2, max_length=40)
    file_url: HttpsUrl = Field(min_length=1, max_length=512)
    file_name: str | None = Field(default=None, max_length=255)
    mime_type: str | None = Field(default=None, max_length=80)
    file_size: int | None = Field(default=None, ge=0)


class SupplierDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    document_type: str
    file_url: str
    verified: bool
    verification_note: str | None


class SupplierDecisionIn(BaseModel):
    status: SupplierStatus
    note: str | None = Field(default=None, max_length=2000)


# ---------------------------------------------------------------------------
# Production batches
# ---------------------------------------------------------------------------


class BatchIngredientIn(BaseModel):
    ingredient_name: str = Field(min_length=1, max_length=160)
    ingredient_name_ta: str | None = Field(default=None, max_length=160)
    source: str | None = Field(default=None, max_length=255)
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=3)
    unit: str | None = Field(default=None, max_length=32)
    notes: str | None = Field(default=None, max_length=1000)


class BatchCreateIn(BaseModel):
    product_type_id: uuid.UUID
    production_location: str | None = Field(default=None, max_length=255)
    production_start_date: date | None = None
    production_completion_date: date | None = None
    preparation_method: str | None = Field(default=None, max_length=4000)
    batch_quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=3)
    unit: str = Field(min_length=1, max_length=32)
    available_quantity_offered: Decimal | None = Field(
        default=None, gt=0, max_digits=14, decimal_places=3
    )
    expected_procurement_price: Decimal | None = Field(
        default=None, gt=0, max_digits=14, decimal_places=2
    )
    storage_method: str | None = Field(default=None, max_length=2000)
    use_before_date: date | None = None
    ingredients: list[BatchIngredientIn] = Field(default_factory=list, max_length=50)


class BatchUpdateIn(BaseModel):
    """Same fields as create, all optional -- only valid while status == draft."""

    production_location: str | None = Field(default=None, max_length=255)
    production_start_date: date | None = None
    production_completion_date: date | None = None
    preparation_method: str | None = Field(default=None, max_length=4000)
    batch_quantity: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=3)
    unit: str | None = Field(default=None, min_length=1, max_length=32)
    available_quantity_offered: Decimal | None = Field(
        default=None, gt=0, max_digits=14, decimal_places=3
    )
    expected_procurement_price: Decimal | None = Field(
        default=None, gt=0, max_digits=14, decimal_places=2
    )
    storage_method: str | None = Field(default=None, max_length=2000)
    use_before_date: date | None = None


class BatchDocumentIn(BaseModel):
    document_type: str = Field(min_length=2, max_length=40)
    file_url: HttpsUrl = Field(min_length=1, max_length=512)
    file_name: str | None = Field(default=None, max_length=255)
    mime_type: str | None = Field(default=None, max_length=80)
    file_size: int | None = Field(default=None, ge=0)
    caption: str | None = Field(default=None, max_length=255)


class BatchIngredientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ingredient_name: str
    ingredient_name_ta: str | None
    source: str | None
    quantity: Decimal | None
    unit: str | None


class BatchDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    document_type: str
    file_url: str
    caption: str | None


class BatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    batch_code: str
    product_type_id: uuid.UUID
    status: str
    batch_quantity: Decimal
    unit: str
    available_quantity_offered: Decimal | None
    expected_procurement_price: Decimal | None
    use_before_date: date | None
    submission_date: datetime | None
    latest_review_note: str | None
    approved_quantity: Decimal | None
    rejected_quantity: Decimal | None
    created_at: datetime
    ingredients: list[BatchIngredientOut] = Field(default_factory=list)
    documents: list[BatchDocumentOut] = Field(default_factory=list)


class BatchDecisionIn(BaseModel):
    status: BatchStatus
    note: str | None = Field(default=None, max_length=2000)
    approved_quantity: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=3)
    rejected_quantity: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=3)


# ---------------------------------------------------------------------------
# Inspection / sampling / testing (QC phase)
# ---------------------------------------------------------------------------


class BatchInspectionIn(BaseModel):
    outcome: Literal["passed", "failed"]
    findings_note: str | None = Field(default=None, max_length=4000)


class BatchInspectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    outcome: str
    findings_note: str | None
    inspected_at: datetime


class BatchSampleIn(BaseModel):
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=3)
    unit: str | None = Field(default=None, max_length=32)
    storage_condition: str | None = Field(default=None, max_length=2000)
    chain_of_custody_note: str | None = Field(default=None, max_length=2000)


class BatchTestResultIn(BaseModel):
    parameter_name: str = Field(min_length=1, max_length=120)
    parameter_name_ta: str | None = Field(default=None, max_length=120)
    expected_limit: dict | None = None
    measured_value: str | None = Field(default=None, max_length=120)
    unit: str | None = Field(default=None, max_length=32)
    pass_fail: bool
    lab_name: str | None = Field(default=None, max_length=160)
    tested_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=2000)


class BatchTestResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    parameter_name: str
    parameter_name_ta: str | None
    expected_limit: dict | None
    measured_value: str | None
    unit: str | None
    pass_fail: bool
    lab_name: str | None
    tested_at: datetime | None


class BatchSampleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    sample_code: str
    collected_at: datetime
    quantity: Decimal | None
    unit: str | None
    storage_condition: str | None
    test_results: list[BatchTestResultOut] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Procurement / inventory (Phase 3)
# ---------------------------------------------------------------------------


class ProcurementOfferIn(BaseModel):
    offered_quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=3)
    unit: str = Field(min_length=1, max_length=32)
    offered_unit_price: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


class ProcurementOfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    batch_id: uuid.UUID
    offered_quantity: Decimal
    unit: str
    offered_unit_price: Decimal
    status: str
    offered_at: datetime
    decided_at: datetime | None
    rejection_reason: str | None


class ProcurementOfferDecisionIn(BaseModel):
    accept: bool
    rejection_reason: str | None = Field(default=None, max_length=2000)


class BatchReceiptIn(BaseModel):
    received_quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=3)
    unit: str = Field(min_length=1, max_length=32)
    condition_note: str | None = Field(default=None, max_length=2000)


class BatchReceiptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    received_quantity: Decimal
    unit: str
    received_at: datetime
    condition_note: str | None


class InventoryMovementIn(BaseModel):
    movement_type: Literal["adjustment", "withdrawal"]
    quantity_delta: Decimal = Field(max_digits=14, decimal_places=3)
    note: str | None = Field(default=None, max_length=2000)


class InventoryMovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    movement_type: str
    quantity_delta: Decimal
    note: str | None
    created_at: datetime


class InventoryLotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    batch_id: uuid.UUID
    product_type_id: uuid.UUID
    quantity_available: Decimal
    unit: str
    unit_cost: Decimal
    created_at: datetime
    movements: list[InventoryMovementOut] = Field(default_factory=list)
