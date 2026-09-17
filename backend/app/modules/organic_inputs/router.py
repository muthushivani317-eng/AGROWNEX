"""Organic Inputs Marketplace API.

Dynamic catalogue (admin-managed, no code change needed for a new category or
product type), supplier onboarding, production-batch submission with a
guarded state machine, QC (inspection/sampling/testing), and now procurement
(offer/accept-or-reject/receive) and inventory tracking off received batches.
Cart/orders (selling inventory onward to farmer-buyers), traceability and
reviews/recalls are still later phases with no routes here yet (docs:
AGROWAI_ORGANIC_INPUTS_MARKETPLACE).

``router`` (prefix "/organic-inputs") is farmer-facing: every farmer-owned
row is scoped to the caller's own ``user_id`` server-side, never trusted from
a path/query parameter, exactly like the FPO partner-feed isolation pattern
in organic_mvp -- a supplier can never fetch another supplier's profile,
documents or batches by guessing an ID.

``admin_router`` (prefix "/admin/organic-inputs") is staff-facing and gated
per action by ``AdminPermission.MANAGE_MARKETPLACE_CATALOG`` (catalogue),
``MANAGE_MARKETPLACE_SUPPLIERS`` (supplier review -- Field Verifier) or
``MANAGE_MARKETPLACE_QC`` (batch review -- Quality Control); Owner/Super Admin
hold every permission already.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from app.core.database import get_session
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.modules.admin.constants import AdminPermission
from app.modules.admin.dependencies import AdminContextDep
from app.modules.admin.models import AuditLog
from app.modules.auth.dependencies import CurrentUser
from app.modules.organic_inputs.constants import (
    BATCH_ADMIN_DECISIONS,
    SUPPLIER_ADMIN_DECISIONS,
    SUPPLIER_STATUS_MAY_SUBMIT_BATCH,
    BatchStatus,
    CatalogStatus,
    InventoryMovementType,
    NewProductRequestStatus,
    OfferStatus,
    SupplierStatus,
)
from app.modules.organic_inputs.models import (
    BatchDocument,
    BatchIngredient,
    BatchInspection,
    BatchProcurementOffer,
    BatchReceipt,
    BatchSample,
    BatchTestResult,
    InventoryLot,
    InventoryMovement,
    MarketplaceCategory,
    MarketplaceProductType,
    NewProductTypeRequest,
    ProductionBatch,
    ProductTypeVersion,
    SupplierDocument,
    SupplierProfile,
)
from app.modules.organic_inputs.schemas import (
    BatchCreateIn,
    BatchDecisionIn,
    BatchDocumentIn,
    BatchInspectionIn,
    BatchOut,
    BatchReceiptIn,
    BatchReceiptOut,
    BatchSampleIn,
    BatchSampleOut,
    BatchTestResultIn,
    BatchTestResultOut,
    BatchUpdateIn,
    CatalogStatusIn,
    CategoryIn,
    CategoryOut,
    InventoryLotOut,
    InventoryMovementIn,
    InventoryMovementOut,
    NewProductTypeRequestDecisionIn,
    NewProductTypeRequestIn,
    NewProductTypeRequestOut,
    ProcurementOfferDecisionIn,
    ProcurementOfferIn,
    ProcurementOfferOut,
    ProductTypeIn,
    ProductTypeOut,
    ProductTypeVersionIn,
    ProductTypeVersionOut,
    SupplierApplyIn,
    SupplierDecisionIn,
    SupplierDocumentIn,
    SupplierDocumentOut,
    SupplierProfileOut,
)
from app.modules.organic_inputs.service import (
    assert_transition_allowed,
    generate_batch_code,
    generate_sample_code,
)
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/organic-inputs", tags=["organic-inputs"])
admin_router = APIRouter(prefix="/admin/organic-inputs", tags=["organic-inputs-admin"])
Session = Annotated[AsyncSession, Depends(get_session)]


def _require_permission(admin, *permissions: AdminPermission) -> None:
    if not any(p.value in admin.permissions for p in permissions):
        raise ForbiddenError("You do not have permission to perform this action.")


def _product_type_out(product_type: MarketplaceProductType) -> ProductTypeOut:
    current = next((v for v in product_type.versions if v.is_current), None)
    return ProductTypeOut(
        id=product_type.id,
        category_id=product_type.category_id,
        slug=product_type.slug,
        name=product_type.name,
        name_ta=product_type.name_ta,
        status=product_type.status,
        current_version=ProductTypeVersionOut.model_validate(current) if current else None,
    )


async def _my_supplier_profile(session: AsyncSession, user_id: uuid.UUID) -> SupplierProfile:
    profile = await session.scalar(
        select(SupplierProfile).where(SupplierProfile.user_id == user_id)
    )
    if profile is None:
        raise NotFoundError("You have not applied as a supplier yet.")
    return profile


async def _my_batch(
    session: AsyncSession, user_id: uuid.UUID, batch_id: uuid.UUID
) -> ProductionBatch:
    batch = await session.scalar(
        select(ProductionBatch)
        .join(SupplierProfile, SupplierProfile.id == ProductionBatch.supplier_id)
        .where(ProductionBatch.id == batch_id, SupplierProfile.user_id == user_id)
    )
    if batch is None:
        raise NotFoundError("Batch not found.")
    return batch


# ---------------------------------------------------------------------------
# Catalogue -- admin
# ---------------------------------------------------------------------------


@admin_router.post("/categories")
async def create_category(body: CategoryIn, session: Session, admin: AdminContextDep):
    _require_permission(admin, AdminPermission.MANAGE_MARKETPLACE_CATALOG)
    existing = await session.scalar(
        select(MarketplaceCategory).where(MarketplaceCategory.slug == body.slug)
    )
    if existing:
        raise ConflictError("A category with this slug already exists.")
    row = MarketplaceCategory(**body.model_dump())
    session.add(row)
    session.add(
        AuditLog(
            admin_id=admin.admin.id,
            role=admin.admin.role,
            action="organic_inputs_category_created",
            target="organic_inputs_category",
            target_id=str(row.id),
            ip_address=admin.ip_address,
            meta={"slug": body.slug},
        )
    )
    await session.commit()
    return CategoryOut.model_validate(row)


@admin_router.post("/product-types")
async def create_product_type(body: ProductTypeIn, session: Session, admin: AdminContextDep):
    _require_permission(admin, AdminPermission.MANAGE_MARKETPLACE_CATALOG)
    category = await session.get(MarketplaceCategory, body.category_id)
    if category is None:
        raise NotFoundError("Category not found.")
    existing = await session.scalar(
        select(MarketplaceProductType).where(MarketplaceProductType.slug == body.slug)
    )
    if existing:
        raise ConflictError("A product type with this slug already exists.")
    row = MarketplaceProductType(**body.model_dump(), status=CatalogStatus.DRAFT.value)
    session.add(row)
    session.add(
        AuditLog(
            admin_id=admin.admin.id,
            role=admin.admin.role,
            action="organic_inputs_product_type_created",
            target="organic_inputs_product_type",
            target_id=str(row.id),
            ip_address=admin.ip_address,
            meta={"slug": body.slug},
        )
    )
    await session.commit()
    return {"id": str(row.id), "slug": row.slug, "status": row.status}


@admin_router.post("/product-types/{product_type_id}/versions")
async def publish_product_type_version(
    product_type_id: uuid.UUID, body: ProductTypeVersionIn, session: Session, admin: AdminContextDep
):
    """Publish a new admin-authored definition. Never edits a past version --
    a batch that already snapshotted an old version keeps referencing it."""
    _require_permission(admin, AdminPermission.MANAGE_MARKETPLACE_CATALOG)
    product_type = await session.get(MarketplaceProductType, product_type_id)
    if product_type is None:
        raise NotFoundError("Product type not found.")
    previous = await session.scalar(
        select(ProductTypeVersion).where(
            ProductTypeVersion.product_type_id == product_type_id,
            ProductTypeVersion.is_current.is_(True),
        )
    )
    next_version = (previous.version + 1) if previous else 1
    if previous:
        previous.is_current = False
    row = ProductTypeVersion(
        product_type_id=product_type_id,
        version=next_version,
        is_current=True,
        **body.model_dump(),
    )
    session.add(row)
    session.add(
        AuditLog(
            admin_id=admin.admin.id,
            role=admin.admin.role,
            action="organic_inputs_product_type_version_published",
            target="organic_inputs_product_type_version",
            target_id=str(row.id),
            ip_address=admin.ip_address,
            meta={"product_type_id": str(product_type_id), "version": next_version},
        )
    )
    await session.commit()
    return {"id": str(row.id), "version": row.version}


@admin_router.post("/product-types/{product_type_id}/status")
async def set_product_type_status(
    product_type_id: uuid.UUID, body: CatalogStatusIn, session: Session, admin: AdminContextDep
):
    """Activate/suspend/archive -- never a physical delete (docs section 2:
    catalogue items connected to suppliers/batches must not be removed)."""
    _require_permission(admin, AdminPermission.MANAGE_MARKETPLACE_CATALOG)
    product_type = await session.get(MarketplaceProductType, product_type_id)
    if product_type is None:
        raise NotFoundError("Product type not found.")
    old_status = product_type.status
    product_type.status = body.status.value
    session.add(
        AuditLog(
            admin_id=admin.admin.id,
            role=admin.admin.role,
            action="organic_inputs_product_type_status_changed",
            target="organic_inputs_product_type",
            target_id=str(product_type.id),
            ip_address=admin.ip_address,
            meta={"old_status": old_status, "new_status": body.status.value},
        )
    )
    await session.commit()
    return {"status": product_type.status}


@admin_router.get("/product-type-requests")
async def list_new_product_requests(
    session: Session,
    admin: AdminContextDep,
    status_filter: Annotated[NewProductRequestStatus | None, Query(alias="status")] = None,
):
    _require_permission(admin, AdminPermission.MANAGE_MARKETPLACE_CATALOG)
    stmt = select(NewProductTypeRequest)
    if status_filter:
        stmt = stmt.where(NewProductTypeRequest.status == status_filter.value)
    rows = (await session.scalars(stmt.order_by(NewProductTypeRequest.created_at.desc()))).all()
    return [NewProductTypeRequestOut.model_validate(row) for row in rows]


@admin_router.post("/product-type-requests/{request_id}/decision")
async def decide_new_product_request(
    request_id: uuid.UUID,
    body: NewProductTypeRequestDecisionIn,
    session: Session,
    admin: AdminContextDep,
):
    _require_permission(admin, AdminPermission.MANAGE_MARKETPLACE_CATALOG)
    row = await session.get(NewProductTypeRequest, request_id)
    if row is None or row.status != NewProductRequestStatus.PENDING.value:
        raise NotFoundError("Pending product type request not found.")
    row.status = body.status.value
    row.review_note = body.review_note
    row.reviewed_by_admin_id = admin.admin.id
    row.reviewed_at = datetime.now(UTC)
    session.add(
        AuditLog(
            admin_id=admin.admin.id,
            role=admin.admin.role,
            action="organic_inputs_product_request_decided",
            target="organic_inputs_new_product_request",
            target_id=str(row.id),
            ip_address=admin.ip_address,
            meta={"status": body.status.value},
        )
    )
    await session.commit()
    return {"status": row.status}


# ---------------------------------------------------------------------------
# Catalogue -- farmer-facing
# ---------------------------------------------------------------------------


@router.get("/categories")
async def list_categories(session: Session, _user: CurrentUser):
    rows = (
        await session.scalars(
            select(MarketplaceCategory)
            .where(
                MarketplaceCategory.status == CatalogStatus.ACTIVE.value,
                MarketplaceCategory.is_deleted.is_(False),
            )
            .order_by(MarketplaceCategory.display_order, MarketplaceCategory.name)
        )
    ).all()
    return [CategoryOut.model_validate(row) for row in rows]


@router.get("/product-types")
async def list_product_types(
    session: Session,
    _user: CurrentUser,
    category_id: uuid.UUID | None = None,
):
    stmt = select(MarketplaceProductType).where(
        MarketplaceProductType.status == CatalogStatus.ACTIVE.value,
        MarketplaceProductType.is_deleted.is_(False),
    )
    if category_id:
        stmt = stmt.where(MarketplaceProductType.category_id == category_id)
    rows = (await session.scalars(stmt.order_by(MarketplaceProductType.name))).all()
    return [_product_type_out(row) for row in rows]


@router.get("/product-types/{product_type_id}")
async def get_product_type(product_type_id: uuid.UUID, session: Session, _user: CurrentUser):
    product_type = await session.get(MarketplaceProductType, product_type_id)
    if product_type is None or product_type.status != CatalogStatus.ACTIVE.value:
        raise NotFoundError("Product type not found.")
    return _product_type_out(product_type)


@router.post("/product-type-requests")
async def submit_new_product_request(
    body: NewProductTypeRequestIn, session: Session, user: CurrentUser
):
    row = NewProductTypeRequest(requested_by_user_id=user.id, **body.model_dump())
    session.add(row)
    session.add(
        AuditLog(
            role="farmer",
            action="organic_inputs_product_request_submitted",
            target="organic_inputs_new_product_request",
            target_id=str(row.id),
            meta={"actor_user_id": str(user.id)},
        )
    )
    await session.commit()
    return NewProductTypeRequestOut.model_validate(row)


@router.get("/my-product-type-requests")
async def my_product_type_requests(session: Session, user: CurrentUser):
    rows = (
        await session.scalars(
            select(NewProductTypeRequest)
            .where(NewProductTypeRequest.requested_by_user_id == user.id)
            .order_by(NewProductTypeRequest.created_at.desc())
        )
    ).all()
    return [NewProductTypeRequestOut.model_validate(row) for row in rows]


# ---------------------------------------------------------------------------
# Supplier onboarding -- farmer-facing
# ---------------------------------------------------------------------------


@router.post("/supplier-profile")
async def apply_as_supplier(body: SupplierApplyIn, session: Session, user: CurrentUser):
    existing = await session.scalar(
        select(SupplierProfile).where(SupplierProfile.user_id == user.id)
    )
    if existing and existing.status != SupplierStatus.DRAFT.value:
        raise ConflictError("A supplier application already exists.")
    if existing:
        for key, value in body.model_dump().items():
            setattr(existing, key, value)
        row = existing
    else:
        row = SupplierProfile(
            user_id=user.id, status=SupplierStatus.DRAFT.value, **body.model_dump()
        )
        row.documents = []
        session.add(row)
    session.add(
        AuditLog(
            role="farmer",
            action="organic_inputs_supplier_drafted",
            target="organic_inputs_supplier_profile",
            target_id=str(row.id),
            meta={"actor_user_id": str(user.id)},
        )
    )
    await session.commit()
    return SupplierProfileOut.model_validate(row)


@router.get("/supplier-profile")
async def my_supplier_profile(session: Session, user: CurrentUser):
    profile = await _my_supplier_profile(session, user.id)
    return SupplierProfileOut.model_validate(profile)


@router.post("/supplier-profile/submit")
async def submit_supplier_profile(session: Session, user: CurrentUser):
    profile = await _my_supplier_profile(session, user.id)
    assert_transition_allowed(
        profile.status,
        SupplierStatus.SUBMITTED.value,
        {SupplierStatus.DRAFT.value: {SupplierStatus.SUBMITTED.value}},
    )
    profile.status = SupplierStatus.SUBMITTED.value
    profile.submitted_at = datetime.now(UTC)
    session.add(
        AuditLog(
            role="farmer",
            action="organic_inputs_supplier_submitted",
            target="organic_inputs_supplier_profile",
            target_id=str(profile.id),
            meta={"actor_user_id": str(user.id)},
        )
    )
    await session.commit()
    return {"status": profile.status}


@router.post("/supplier-profile/documents")
async def add_supplier_document(body: SupplierDocumentIn, session: Session, user: CurrentUser):
    profile = await _my_supplier_profile(session, user.id)
    row = SupplierDocument(supplier_id=profile.id, **body.model_dump())
    session.add(row)
    await session.commit()
    return SupplierDocumentOut.model_validate(row)


@router.get("/supplier-profile/documents")
async def list_supplier_documents(session: Session, user: CurrentUser):
    profile = await _my_supplier_profile(session, user.id)
    return [SupplierDocumentOut.model_validate(doc) for doc in profile.documents]


# ---------------------------------------------------------------------------
# Supplier onboarding -- admin (Field Verifier)
# ---------------------------------------------------------------------------


@admin_router.get("/suppliers")
async def list_suppliers(
    session: Session,
    admin: AdminContextDep,
    status_filter: Annotated[SupplierStatus | None, Query(alias="status")] = None,
):
    _require_permission(
        admin, AdminPermission.MANAGE_MARKETPLACE_SUPPLIERS, AdminPermission.MANAGE_MARKETPLACE_QC
    )
    stmt = select(SupplierProfile)
    if status_filter:
        stmt = stmt.where(SupplierProfile.status == status_filter.value)
    rows = (await session.scalars(stmt.order_by(SupplierProfile.created_at.desc()))).all()
    return [SupplierProfileOut.model_validate(row) for row in rows]


@admin_router.get("/suppliers/{supplier_id}")
async def get_supplier(supplier_id: uuid.UUID, session: Session, admin: AdminContextDep):
    _require_permission(
        admin, AdminPermission.MANAGE_MARKETPLACE_SUPPLIERS, AdminPermission.MANAGE_MARKETPLACE_QC
    )
    profile = await session.get(SupplierProfile, supplier_id)
    if profile is None:
        raise NotFoundError("Supplier not found.")
    out = SupplierProfileOut.model_validate(profile).model_dump()
    out["documents"] = [SupplierDocumentOut.model_validate(doc) for doc in profile.documents]
    return out


@admin_router.post("/suppliers/{supplier_id}/decision")
async def decide_supplier(
    supplier_id: uuid.UUID, body: SupplierDecisionIn, session: Session, admin: AdminContextDep
):
    _require_permission(admin, AdminPermission.MANAGE_MARKETPLACE_SUPPLIERS)
    profile = await session.get(SupplierProfile, supplier_id)
    if profile is None:
        raise NotFoundError("Supplier not found.")
    assert_transition_allowed(
        profile.status,
        body.status.value,
        {k.value: {v.value for v in vs} for k, vs in SUPPLIER_ADMIN_DECISIONS.items()},
    )
    profile.status = body.status.value
    profile.reviewed_by_admin_id = admin.admin.id
    profile.reviewed_at = datetime.now(UTC)
    if body.status == SupplierStatus.REJECTED:
        profile.rejection_reason = body.note
    if body.status == SupplierStatus.SUSPENDED:
        profile.suspension_reason = body.note
    session.add(
        AuditLog(
            admin_id=admin.admin.id,
            role=admin.admin.role,
            action="organic_inputs_supplier_decided",
            target="organic_inputs_supplier_profile",
            target_id=str(profile.id),
            ip_address=admin.ip_address,
            meta={"status": body.status.value, "note": body.note},
        )
    )
    await session.commit()
    return {"status": profile.status}


# ---------------------------------------------------------------------------
# Production batches -- farmer-facing (seller)
# ---------------------------------------------------------------------------


@router.post("/batches")
async def create_batch(body: BatchCreateIn, session: Session, user: CurrentUser):
    profile = await _my_supplier_profile(session, user.id)
    if profile.status != SUPPLIER_STATUS_MAY_SUBMIT_BATCH.value:
        raise ForbiddenError("Only an approved supplier may create a batch.")
    product_type = await session.get(MarketplaceProductType, body.product_type_id)
    if product_type is None or product_type.status != CatalogStatus.ACTIVE.value:
        raise NotFoundError("Product type not found or not active.")
    current_version = next((v for v in product_type.versions if v.is_current), None)
    if current_version is None:
        raise ValidationError("This product type has no published definition yet.")
    payload = body.model_dump(exclude={"ingredients"})
    row = ProductionBatch(
        batch_code=generate_batch_code(),
        supplier_id=profile.id,
        product_type_version_id=current_version.id,
        status=BatchStatus.DRAFT.value,
        **payload,
    )
    row.ingredients = [BatchIngredient(**i.model_dump()) for i in body.ingredients]
    row.documents = []
    session.add(row)
    session.add(
        AuditLog(
            role="farmer",
            action="organic_inputs_batch_created",
            target="organic_inputs_production_batch",
            target_id=str(row.id),
            meta={"actor_user_id": str(user.id), "product_type_id": str(body.product_type_id)},
        )
    )
    await session.commit()
    return BatchOut.model_validate(row)


@router.get("/batches")
async def list_my_batches(session: Session, user: CurrentUser):
    rows = (
        await session.scalars(
            select(ProductionBatch)
            .join(SupplierProfile, SupplierProfile.id == ProductionBatch.supplier_id)
            .where(SupplierProfile.user_id == user.id, ProductionBatch.is_deleted.is_(False))
            .order_by(ProductionBatch.created_at.desc())
        )
    ).all()
    return [BatchOut.model_validate(row) for row in rows]


@router.get("/batches/{batch_id}")
async def get_my_batch(batch_id: uuid.UUID, session: Session, user: CurrentUser):
    batch = await _my_batch(session, user.id, batch_id)
    return BatchOut.model_validate(batch)


@router.patch("/batches/{batch_id}")
async def update_batch_draft(
    batch_id: uuid.UUID, body: BatchUpdateIn, session: Session, user: CurrentUser
):
    batch = await _my_batch(session, user.id, batch_id)
    if batch.status != BatchStatus.DRAFT.value:
        raise ConflictError("Only a draft batch can be edited.")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(batch, key, value)
    await session.commit()
    return BatchOut.model_validate(batch)


@router.post("/batches/{batch_id}/documents")
async def add_batch_document(
    batch_id: uuid.UUID, body: BatchDocumentIn, session: Session, user: CurrentUser
):
    batch = await _my_batch(session, user.id, batch_id)
    if batch.status != BatchStatus.DRAFT.value:
        raise ConflictError("Documents can only be added to a draft batch.")
    row = BatchDocument(batch_id=batch.id, **body.model_dump())
    session.add(row)
    await session.commit()
    return {"id": str(row.id)}


@router.post("/batches/{batch_id}/submit")
async def submit_batch(batch_id: uuid.UUID, session: Session, user: CurrentUser):
    batch = await _my_batch(session, user.id, batch_id)
    assert_transition_allowed(
        batch.status,
        BatchStatus.SUBMITTED.value,
        {BatchStatus.DRAFT.value: {BatchStatus.SUBMITTED.value}},
    )
    batch.status = BatchStatus.SUBMITTED.value
    batch.submission_date = datetime.now(UTC)
    session.add(
        AuditLog(
            role="farmer",
            action="organic_inputs_batch_submitted",
            target="organic_inputs_production_batch",
            target_id=str(batch.id),
            meta={"actor_user_id": str(user.id)},
        )
    )
    await session.commit()
    return {"status": batch.status}


@router.get("/batches/{batch_id}/procurement-offer")
async def get_my_procurement_offer(batch_id: uuid.UUID, session: Session, user: CurrentUser):
    batch = await _my_batch(session, user.id, batch_id)
    offer = await session.scalar(
        select(BatchProcurementOffer).where(BatchProcurementOffer.batch_id == batch.id)
    )
    if offer is None:
        raise NotFoundError("No procurement offer for this batch yet.")
    return ProcurementOfferOut.model_validate(offer)


@router.post("/batches/{batch_id}/procurement-offer/decision")
async def decide_procurement_offer(
    batch_id: uuid.UUID,
    body: ProcurementOfferDecisionIn,
    session: Session,
    user: CurrentUser,
):
    """The SUPPLIER's own decision on AgrowAI's offer -- drives
    PROCUREMENT_OFFERED -> OFFER_ACCEPTED/OFFER_REJECTED. decide_batch (an
    admin endpoint) cannot grant either outcome; only the batch's own owner
    may accept or reject an offer made to them. A rejected offer is final in
    this phase -- BATCH_TRANSITIONS has no edge back out of OFFER_REJECTED,
    so there is no re-offer/renegotiation loop yet."""
    batch = await _my_batch(session, user.id, batch_id)
    if batch.status != BatchStatus.PROCUREMENT_OFFERED.value:
        raise ConflictError("This batch has no pending procurement offer to decide.")
    offer = await session.scalar(
        select(BatchProcurementOffer).where(
            BatchProcurementOffer.batch_id == batch.id,
            BatchProcurementOffer.status == OfferStatus.OFFERED.value,
        )
    )
    if offer is None:
        raise NotFoundError("No pending procurement offer found for this batch.")
    offer.status = OfferStatus.ACCEPTED.value if body.accept else OfferStatus.REJECTED.value
    offer.decided_at = datetime.now(UTC)
    if not body.accept:
        offer.rejection_reason = body.rejection_reason
    batch.status = (
        BatchStatus.OFFER_ACCEPTED.value if body.accept else BatchStatus.OFFER_REJECTED.value
    )
    session.add(
        AuditLog(
            role="farmer",
            action="organic_inputs_procurement_offer_decided",
            target="organic_inputs_production_batch",
            target_id=str(batch.id),
            meta={"actor_user_id": str(user.id), "accepted": body.accept},
        )
    )
    await session.commit()
    return {"status": batch.status}


# ---------------------------------------------------------------------------
# Production batches -- admin (Quality Control / Field Verifier)
# ---------------------------------------------------------------------------


@admin_router.get("/batches")
async def list_batches(
    session: Session,
    admin: AdminContextDep,
    status_filter: Annotated[BatchStatus | None, Query(alias="status")] = None,
):
    _require_permission(
        admin,
        AdminPermission.MANAGE_MARKETPLACE_QC,
        AdminPermission.MANAGE_MARKETPLACE_SUPPLIERS,
        AdminPermission.MANAGE_MARKETPLACE_PROCUREMENT,
    )
    stmt = select(ProductionBatch).where(ProductionBatch.is_deleted.is_(False))
    if status_filter:
        stmt = stmt.where(ProductionBatch.status == status_filter.value)
    rows = (await session.scalars(stmt.order_by(ProductionBatch.created_at.desc()))).all()
    return [BatchOut.model_validate(row) for row in rows]


@admin_router.get("/batches/{batch_id}")
async def get_batch(batch_id: uuid.UUID, session: Session, admin: AdminContextDep):
    _require_permission(
        admin,
        AdminPermission.MANAGE_MARKETPLACE_QC,
        AdminPermission.MANAGE_MARKETPLACE_SUPPLIERS,
        AdminPermission.MANAGE_MARKETPLACE_PROCUREMENT,
    )
    batch = await session.get(ProductionBatch, batch_id)
    if batch is None:
        raise NotFoundError("Batch not found.")
    return BatchOut.model_validate(batch)


@admin_router.post("/batches/{batch_id}/decision")
async def decide_batch(
    batch_id: uuid.UUID, body: BatchDecisionIn, session: Session, admin: AdminContextDep
):
    """Review-stage decisions (docs: acceptance criteria #5 -- a batch cannot
    be sold without inspection/QC approval), the final testing-outcome
    decision (TESTING -> RETEST_REQUIRED/APPROVED/PARTIALLY_APPROVED/REJECTED),
    and the post-receipt inventory judgement calls (RECEIVED -> QUARANTINED/
    RELEASED_FOR_SALE, QUARANTINED -> RELEASED_FOR_SALE/REJECTED,
    RELEASED_FOR_SALE -> SOLD_OUT/EXPIRED/RECALLED) that need no supporting
    evidence record of their own. The testing outcome requires at least one
    real BatchTestResult already recorded via POST
    .../samples/{sample_id}/test-results -- it can never be granted from
    nothing. PROCUREMENT_OFFERED/OFFER_ACCEPTED/OFFER_REJECTED/RECEIVED are
    deliberately NOT reachable here -- see the dedicated procurement-offer,
    procurement-offer/decision and receipt endpoints below."""
    _require_permission(
        admin,
        AdminPermission.MANAGE_MARKETPLACE_QC,
        AdminPermission.MANAGE_MARKETPLACE_SUPPLIERS,
        AdminPermission.MANAGE_MARKETPLACE_PROCUREMENT,
    )
    batch = await session.get(ProductionBatch, batch_id)
    if batch is None:
        raise NotFoundError("Batch not found.")
    if batch.status == BatchStatus.TESTING.value:
        has_result = await session.scalar(
            select(BatchTestResult.id).where(BatchTestResult.batch_id == batch.id).limit(1)
        )
        if has_result is None:
            raise ValidationError(
                "Cannot decide a testing outcome without at least one recorded test result."
            )
    assert_transition_allowed(
        batch.status,
        body.status.value,
        {k.value: {v.value for v in vs} for k, vs in BATCH_ADMIN_DECISIONS.items()},
    )
    batch.status = body.status.value
    batch.latest_review_note = body.note
    if body.approved_quantity is not None:
        batch.approved_quantity = body.approved_quantity
    if body.rejected_quantity is not None:
        batch.rejected_quantity = body.rejected_quantity
    session.add(
        AuditLog(
            admin_id=admin.admin.id,
            role=admin.admin.role,
            action="organic_inputs_batch_decided",
            target="organic_inputs_production_batch",
            target_id=str(batch.id),
            ip_address=admin.ip_address,
            meta={"status": body.status.value, "note": body.note},
        )
    )
    await session.commit()
    return {"status": batch.status}


# ---------------------------------------------------------------------------
# Inspection / sampling / testing -- admin (QC phase)
# ---------------------------------------------------------------------------


@admin_router.post("/batches/{batch_id}/inspection")
async def record_batch_inspection(
    batch_id: uuid.UUID,
    body: BatchInspectionIn,
    session: Session,
    admin: AdminContextDep,
):
    """Records the one physical/site inspection a batch gets and drives the
    INSPECTION_REQUIRED -> INSPECTION_COMPLETED/REJECTED transition from it --
    this is the only way to leave INSPECTION_REQUIRED; decide_batch cannot."""
    _require_permission(
        admin, AdminPermission.MANAGE_MARKETPLACE_QC, AdminPermission.MANAGE_MARKETPLACE_SUPPLIERS
    )
    batch = await session.get(ProductionBatch, batch_id)
    if batch is None:
        raise NotFoundError("Batch not found.")
    if batch.status != BatchStatus.INSPECTION_REQUIRED.value:
        raise ConflictError("This batch is not awaiting inspection.")
    row = BatchInspection(
        batch_id=batch.id,
        inspector_admin_id=admin.admin.id,
        inspected_at=datetime.now(UTC),
        outcome=body.outcome,
        findings_note=body.findings_note,
    )
    session.add(row)
    target_status = (
        BatchStatus.INSPECTION_COMPLETED if body.outcome == "passed" else BatchStatus.REJECTED
    )
    batch.status = target_status.value
    if target_status == BatchStatus.REJECTED:
        batch.latest_review_note = body.findings_note
    session.add(
        AuditLog(
            admin_id=admin.admin.id,
            role=admin.admin.role,
            action="organic_inputs_batch_inspected",
            target="organic_inputs_production_batch",
            target_id=str(batch.id),
            ip_address=admin.ip_address,
            meta={"outcome": body.outcome},
        )
    )
    await session.commit()
    return {"status": batch.status, "inspection_id": str(row.id)}


@admin_router.post("/batches/{batch_id}/samples")
async def collect_batch_sample(
    batch_id: uuid.UUID,
    body: BatchSampleIn,
    session: Session,
    admin: AdminContextDep,
):
    """Records a physical sample drawn for lab testing and drives
    INSPECTION_COMPLETED/RETEST_REQUIRED -> SAMPLE_COLLECTED -- the only way
    to reach SAMPLE_COLLECTED; decide_batch cannot grant it directly."""
    _require_permission(admin, AdminPermission.MANAGE_MARKETPLACE_QC)
    batch = await session.get(ProductionBatch, batch_id)
    if batch is None:
        raise NotFoundError("Batch not found.")
    if batch.status not in {
        BatchStatus.INSPECTION_COMPLETED.value,
        BatchStatus.RETEST_REQUIRED.value,
    }:
        raise ConflictError(
            "A sample can only be collected after inspection or when a retest is required."
        )
    row = BatchSample(
        batch_id=batch.id,
        sample_code=generate_sample_code(),
        collected_by_admin_id=admin.admin.id,
        collected_at=datetime.now(UTC),
        **body.model_dump(),
    )
    row.test_results = []
    session.add(row)
    batch.status = BatchStatus.SAMPLE_COLLECTED.value
    session.add(
        AuditLog(
            admin_id=admin.admin.id,
            role=admin.admin.role,
            action="organic_inputs_sample_collected",
            target="organic_inputs_production_batch",
            target_id=str(batch.id),
            ip_address=admin.ip_address,
            meta={"sample_id": str(row.id), "sample_code": row.sample_code},
        )
    )
    await session.commit()
    return BatchSampleOut.model_validate(row)


@admin_router.get("/batches/{batch_id}/samples")
async def list_batch_samples(batch_id: uuid.UUID, session: Session, admin: AdminContextDep):
    _require_permission(
        admin, AdminPermission.MANAGE_MARKETPLACE_QC, AdminPermission.MANAGE_MARKETPLACE_SUPPLIERS
    )
    rows = (
        await session.scalars(
            select(BatchSample)
            .where(BatchSample.batch_id == batch_id)
            .order_by(BatchSample.created_at)
        )
    ).all()
    return [BatchSampleOut.model_validate(row) for row in rows]


@admin_router.post("/batches/{batch_id}/samples/{sample_id}/test-results")
async def add_batch_test_result(
    batch_id: uuid.UUID,
    sample_id: uuid.UUID,
    body: BatchTestResultIn,
    session: Session,
    admin: AdminContextDep,
):
    """Records one lab-tested parameter result and drives
    SAMPLE_COLLECTED -> TESTING (first result only; further results while
    already TESTING don't re-transition). ``pass_fail`` is the QC admin's own
    call -- never computed from ``measured_value``/``expected_limit`` here."""
    _require_permission(admin, AdminPermission.MANAGE_MARKETPLACE_QC)
    batch = await session.get(ProductionBatch, batch_id)
    if batch is None:
        raise NotFoundError("Batch not found.")
    sample = await session.get(BatchSample, sample_id)
    if sample is None or sample.batch_id != batch.id:
        raise NotFoundError("Sample not found for this batch.")
    if batch.status not in {BatchStatus.SAMPLE_COLLECTED.value, BatchStatus.TESTING.value}:
        raise ConflictError("Test results can only be recorded once a sample has been collected.")
    row = BatchTestResult(
        sample_id=sample.id,
        batch_id=batch.id,
        entered_by_admin_id=admin.admin.id,
        tested_at=body.tested_at or datetime.now(UTC),
        **body.model_dump(exclude={"tested_at"}),
    )
    session.add(row)
    if batch.status == BatchStatus.SAMPLE_COLLECTED.value:
        batch.status = BatchStatus.TESTING.value
    session.add(
        AuditLog(
            admin_id=admin.admin.id,
            role=admin.admin.role,
            action="organic_inputs_test_result_recorded",
            target="organic_inputs_production_batch",
            target_id=str(batch.id),
            ip_address=admin.ip_address,
            meta={
                "sample_id": str(sample.id),
                "parameter_name": body.parameter_name,
                "pass_fail": body.pass_fail,
            },
        )
    )
    await session.commit()
    return BatchTestResultOut.model_validate(row)


# ---------------------------------------------------------------------------
# Procurement / inventory -- admin (Phase 3)
# ---------------------------------------------------------------------------


@admin_router.post("/batches/{batch_id}/procurement-offer")
async def create_procurement_offer(
    batch_id: uuid.UUID,
    body: ProcurementOfferIn,
    session: Session,
    admin: AdminContextDep,
):
    """Extends AgrowAI's offer to buy from an APPROVED/PARTIALLY_APPROVED
    batch and drives that -> PROCUREMENT_OFFERED -- the only way to leave
    APPROVED/PARTIALLY_APPROVED; decide_batch cannot grant PROCUREMENT_OFFERED
    directly. A batch can only ever get one offer in this phase -- see
    OfferStatus."""
    _require_permission(admin, AdminPermission.MANAGE_MARKETPLACE_PROCUREMENT)
    batch = await session.get(ProductionBatch, batch_id)
    if batch is None:
        raise NotFoundError("Batch not found.")
    if batch.status not in {BatchStatus.APPROVED.value, BatchStatus.PARTIALLY_APPROVED.value}:
        raise ConflictError("An offer can only be made on an approved batch.")
    existing = await session.scalar(
        select(BatchProcurementOffer.id).where(BatchProcurementOffer.batch_id == batch.id).limit(1)
    )
    if existing is not None:
        raise ConflictError("This batch already has a procurement offer.")
    if body.unit != batch.unit:
        raise ValidationError("Offer unit must match the batch's own unit.")
    ceiling = batch.approved_quantity or batch.batch_quantity
    if body.offered_quantity > ceiling:
        raise ValidationError("Offered quantity cannot exceed the batch's approved quantity.")
    row = BatchProcurementOffer(
        batch_id=batch.id,
        offered_by_admin_id=admin.admin.id,
        offered_at=datetime.now(UTC),
        status=OfferStatus.OFFERED.value,
        **body.model_dump(),
    )
    session.add(row)
    batch.status = BatchStatus.PROCUREMENT_OFFERED.value
    session.add(
        AuditLog(
            admin_id=admin.admin.id,
            role=admin.admin.role,
            action="organic_inputs_procurement_offer_created",
            target="organic_inputs_production_batch",
            target_id=str(batch.id),
            ip_address=admin.ip_address,
            meta={
                "offer_id": str(row.id),
                "offered_quantity": str(body.offered_quantity),
                "offered_unit_price": str(body.offered_unit_price),
            },
        )
    )
    await session.commit()
    return ProcurementOfferOut.model_validate(row)


@admin_router.get("/batches/{batch_id}/procurement-offer")
async def get_procurement_offer(batch_id: uuid.UUID, session: Session, admin: AdminContextDep):
    _require_permission(
        admin,
        AdminPermission.MANAGE_MARKETPLACE_PROCUREMENT,
        AdminPermission.MANAGE_MARKETPLACE_QC,
        AdminPermission.MANAGE_MARKETPLACE_SUPPLIERS,
    )
    offer = await session.scalar(
        select(BatchProcurementOffer).where(BatchProcurementOffer.batch_id == batch_id)
    )
    if offer is None:
        raise NotFoundError("No procurement offer for this batch yet.")
    return ProcurementOfferOut.model_validate(offer)


@admin_router.post("/batches/{batch_id}/receipt")
async def record_batch_receipt(
    batch_id: uuid.UUID,
    body: BatchReceiptIn,
    session: Session,
    admin: AdminContextDep,
):
    """Records the physical receipt of a procured batch and drives
    OFFER_ACCEPTED -> RECEIVED -- the only way to reach RECEIVED; decide_batch
    cannot grant it directly. Also creates the batch's InventoryLot together
    with its opening RECEIPT movement, so a lot never exists without a
    recorded reason for its starting balance."""
    _require_permission(admin, AdminPermission.MANAGE_MARKETPLACE_PROCUREMENT)
    batch = await session.get(ProductionBatch, batch_id)
    if batch is None:
        raise NotFoundError("Batch not found.")
    if batch.status != BatchStatus.OFFER_ACCEPTED.value:
        raise ConflictError("This batch has no accepted offer awaiting receipt.")
    offer = await session.scalar(
        select(BatchProcurementOffer).where(
            BatchProcurementOffer.batch_id == batch.id,
            BatchProcurementOffer.status == OfferStatus.ACCEPTED.value,
        )
    )
    if offer is None:
        raise NotFoundError("No accepted procurement offer found for this batch.")
    if body.unit != offer.unit:
        raise ValidationError("Received unit must match the accepted offer's unit.")
    if body.received_quantity > offer.offered_quantity:
        raise ValidationError("Received quantity cannot exceed the accepted offer's quantity.")
    receipt = BatchReceipt(
        batch_id=batch.id,
        offer_id=offer.id,
        received_by_admin_id=admin.admin.id,
        received_at=datetime.now(UTC),
        **body.model_dump(),
    )
    session.add(receipt)
    await session.flush()
    lot = InventoryLot(
        batch_id=batch.id,
        product_type_id=batch.product_type_id,
        receipt_id=receipt.id,
        quantity_available=body.received_quantity,
        unit=body.unit,
        unit_cost=offer.offered_unit_price,
    )
    lot.movements = [
        InventoryMovement(
            movement_type=InventoryMovementType.RECEIPT.value,
            quantity_delta=body.received_quantity,
            note="Initial receipt.",
            performed_by_admin_id=admin.admin.id,
        )
    ]
    session.add(lot)
    batch.status = BatchStatus.RECEIVED.value
    session.add(
        AuditLog(
            admin_id=admin.admin.id,
            role=admin.admin.role,
            action="organic_inputs_batch_received",
            target="organic_inputs_production_batch",
            target_id=str(batch.id),
            ip_address=admin.ip_address,
            meta={
                "receipt_id": str(receipt.id),
                "received_quantity": str(body.received_quantity),
            },
        )
    )
    await session.commit()
    return BatchReceiptOut.model_validate(receipt)


@admin_router.get("/batches/{batch_id}/inventory")
async def get_batch_inventory(batch_id: uuid.UUID, session: Session, admin: AdminContextDep):
    _require_permission(
        admin,
        AdminPermission.MANAGE_MARKETPLACE_PROCUREMENT,
        AdminPermission.MANAGE_MARKETPLACE_QC,
        AdminPermission.MANAGE_MARKETPLACE_SUPPLIERS,
    )
    lot = await session.scalar(select(InventoryLot).where(InventoryLot.batch_id == batch_id))
    if lot is None:
        raise NotFoundError("No inventory lot for this batch yet.")
    return InventoryLotOut.model_validate(lot)


@admin_router.get("/inventory")
async def list_inventory(
    session: Session,
    admin: AdminContextDep,
    product_type_id: uuid.UUID | None = None,
):
    _require_permission(
        admin,
        AdminPermission.MANAGE_MARKETPLACE_PROCUREMENT,
        AdminPermission.MANAGE_MARKETPLACE_QC,
        AdminPermission.MANAGE_MARKETPLACE_SUPPLIERS,
    )
    stmt = select(InventoryLot)
    if product_type_id:
        stmt = stmt.where(InventoryLot.product_type_id == product_type_id)
    rows = (await session.scalars(stmt.order_by(InventoryLot.created_at.desc()))).all()
    return [InventoryLotOut.model_validate(row) for row in rows]


@admin_router.post("/batches/{batch_id}/inventory/movements")
async def record_inventory_movement(
    batch_id: uuid.UUID,
    body: InventoryMovementIn,
    session: Session,
    admin: AdminContextDep,
):
    """Adjusts an inventory lot's available quantity for a reason other than
    its opening receipt -- RECEIPT movements are only ever written by
    record_batch_receipt. If this drains the lot to zero while the batch is
    RELEASED_FOR_SALE, the batch is moved straight to SOLD_OUT: this repo has
    no cart/orders yet (docs section 1) to trigger that transition on its
    own, and leaving an empty lot marked "for sale" would be a stale status,
    not an honest one."""
    _require_permission(admin, AdminPermission.MANAGE_MARKETPLACE_PROCUREMENT)
    batch = await session.get(ProductionBatch, batch_id)
    if batch is None:
        raise NotFoundError("Batch not found.")
    lot = await session.scalar(select(InventoryLot).where(InventoryLot.batch_id == batch_id))
    if lot is None:
        raise NotFoundError("No inventory lot for this batch yet.")
    new_quantity = lot.quantity_available + body.quantity_delta
    if new_quantity < 0:
        raise ValidationError("This movement would take available quantity below zero.")
    movement = InventoryMovement(
        lot_id=lot.id,
        movement_type=body.movement_type,
        quantity_delta=body.quantity_delta,
        note=body.note,
        performed_by_admin_id=admin.admin.id,
    )
    session.add(movement)
    lot.quantity_available = new_quantity
    if new_quantity == 0 and batch.status == BatchStatus.RELEASED_FOR_SALE.value:
        batch.status = BatchStatus.SOLD_OUT.value
    session.add(
        AuditLog(
            admin_id=admin.admin.id,
            role=admin.admin.role,
            action="organic_inputs_inventory_movement_recorded",
            target="organic_inputs_production_batch",
            target_id=str(batch.id),
            ip_address=admin.ip_address,
            meta={"movement_type": body.movement_type, "quantity_delta": str(body.quantity_delta)},
        )
    )
    await session.commit()
    return InventoryMovementOut.model_validate(movement)
