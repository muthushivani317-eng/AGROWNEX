"""Organic Inputs Marketplace foundation: catalogue, supplier onboarding, batches.

Covers: state-machine guards (no skipping straight to APPROVED without QC),
ownership isolation (one supplier can never touch another's profile/batch),
and staff-permission gating (Field Verifier vs Quality Control vs Catalog).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.modules.admin.constants import AdminRole, permissions_for
from app.modules.admin.models import AdminUser
from app.modules.admin.service import AdminContext
from app.modules.auth.models import User
from app.modules.organic_inputs.constants import (
    BatchStatus,
    CatalogStatus,
    NewProductRequestStatus,
    SupplierStatus,
)
from app.modules.organic_inputs.models import MarketplaceProductType
from app.modules.organic_inputs.router import (
    add_batch_document,
    apply_as_supplier,
    create_batch,
    create_category,
    create_product_type,
    decide_batch,
    decide_new_product_request,
    decide_supplier,
    get_my_batch,
    my_supplier_profile,
    publish_product_type_version,
    set_product_type_status,
    submit_batch,
    submit_new_product_request,
    submit_supplier_profile,
    update_batch_draft,
)
from app.modules.organic_inputs.schemas import (
    BatchCreateIn,
    BatchDecisionIn,
    BatchDocumentIn,
    BatchUpdateIn,
    CatalogStatusIn,
    CategoryIn,
    NewProductTypeRequestDecisionIn,
    NewProductTypeRequestIn,
    ProductTypeIn,
    ProductTypeVersionIn,
    SupplierApplyIn,
    SupplierDecisionIn,
)


def _admin(user: User, role: AdminRole) -> AdminContext:
    admin_user = AdminUser(user_id=user.id, role=role.value)
    return AdminContext(admin=admin_user, permissions=frozenset(permissions_for(role.value)))


async def _seed_catalog(db_session, owner_ctx):
    category = await create_category(
        CategoryIn(slug="liquid-inputs", name="Liquid organic inputs"), db_session, owner_ctx
    )
    product_type = await create_product_type(
        ProductTypeIn(category_id=category.id, slug="fish-amino-acid", name="Fish amino acid"),
        db_session,
        owner_ctx,
    )
    product_type_id = uuid.UUID(product_type["id"])
    await publish_product_type_version(
        product_type_id,
        ProductTypeVersionIn(unit_of_measurement="litre", allowed_pack_sizes=["1L", "5L"]),
        db_session,
        owner_ctx,
    )
    await set_product_type_status(
        product_type_id, CatalogStatusIn(status=CatalogStatus.ACTIVE), db_session, owner_ctx
    )
    return category, product_type_id


async def _approve_supplier(db_session, farmer: User, owner_ctx) -> None:
    await apply_as_supplier(SupplierApplyIn(district="Erode"), db_session, farmer)
    await submit_supplier_profile(db_session, farmer)
    profile = await my_supplier_profile(db_session, farmer)
    await decide_supplier(
        profile.id, SupplierDecisionIn(status=SupplierStatus.UNDER_REVIEW), db_session, owner_ctx
    )
    await decide_supplier(
        profile.id,
        SupplierDecisionIn(status=SupplierStatus.INSPECTION_SCHEDULED),
        db_session,
        owner_ctx,
    )
    await decide_supplier(
        profile.id,
        SupplierDecisionIn(status=SupplierStatus.INSPECTION_COMPLETED),
        db_session,
        owner_ctx,
    )
    await decide_supplier(
        profile.id, SupplierDecisionIn(status=SupplierStatus.APPROVED), db_session, owner_ctx
    )


@pytest.mark.asyncio
async def test_supplier_cannot_skip_straight_to_approved(db_session):
    farmer = User(firebase_uid="marketplace-farmer-1", status="active")
    owner_user = User(firebase_uid="marketplace-owner-1", status="active")
    db_session.add_all([farmer, owner_user])
    await db_session.flush()
    owner_ctx = _admin(owner_user, AdminRole.OWNER)

    await apply_as_supplier(SupplierApplyIn(district="Erode"), db_session, farmer)
    profile = await my_supplier_profile(db_session, farmer)
    assert profile.status == SupplierStatus.DRAFT.value

    with pytest.raises(ValidationError):
        await decide_supplier(
            profile.id, SupplierDecisionIn(status=SupplierStatus.APPROVED), db_session, owner_ctx
        )


@pytest.mark.asyncio
async def test_batch_cannot_skip_qc_and_only_approved_supplier_may_submit(db_session):
    farmer = User(firebase_uid="marketplace-farmer-2", status="active")
    owner_user = User(firebase_uid="marketplace-owner-2", status="active")
    db_session.add_all([farmer, owner_user])
    await db_session.flush()
    owner_ctx = _admin(owner_user, AdminRole.OWNER)
    _category, product_type_id = await _seed_catalog(db_session, owner_ctx)

    # A supplier that only just applied (DRAFT) cannot create a batch.
    await apply_as_supplier(SupplierApplyIn(district="Erode"), db_session, farmer)
    with pytest.raises(ForbiddenError):
        await create_batch(
            BatchCreateIn(product_type_id=product_type_id, batch_quantity="50", unit="litre"),
            db_session,
            farmer,
        )

    await _approve_supplier(db_session, farmer, owner_ctx)

    batch = await create_batch(
        BatchCreateIn(product_type_id=product_type_id, batch_quantity="50", unit="litre"),
        db_session,
        farmer,
    )
    assert batch.status == BatchStatus.DRAFT.value
    await submit_batch(batch.id, db_session, farmer)

    # Editing a submitted (non-draft) batch is rejected.
    with pytest.raises(ConflictError):
        await update_batch_draft(batch.id, BatchUpdateIn(unit="kg"), db_session, farmer)

    await decide_batch(
        batch.id, BatchDecisionIn(status=BatchStatus.UNDER_REVIEW), db_session, owner_ctx
    )
    await decide_batch(
        batch.id, BatchDecisionIn(status=BatchStatus.INSPECTION_REQUIRED), db_session, owner_ctx
    )
    # Nothing in this phase can grant APPROVED -- that needs the QC phase's
    # inspection/testing models, which don't exist yet.
    with pytest.raises(ValidationError):
        await decide_batch(
            batch.id, BatchDecisionIn(status=BatchStatus.APPROVED), db_session, owner_ctx
        )


@pytest.mark.asyncio
async def test_supplier_and_batch_ownership_isolation(db_session):
    farmer_a = User(firebase_uid="marketplace-farmer-a", status="active")
    farmer_b = User(firebase_uid="marketplace-farmer-b", status="active")
    owner_user = User(firebase_uid="marketplace-owner-3", status="active")
    db_session.add_all([farmer_a, farmer_b, owner_user])
    await db_session.flush()
    owner_ctx = _admin(owner_user, AdminRole.OWNER)
    _category, product_type_id = await _seed_catalog(db_session, owner_ctx)

    await _approve_supplier(db_session, farmer_a, owner_ctx)
    batch = await create_batch(
        BatchCreateIn(product_type_id=product_type_id, batch_quantity="20", unit="litre"),
        db_session,
        farmer_a,
    )

    # farmer_b has no supplier profile at all.
    with pytest.raises(NotFoundError):
        await my_supplier_profile(db_session, farmer_b)

    # farmer_b cannot see, edit, submit or add documents to farmer_a's batch.
    with pytest.raises(NotFoundError):
        await get_my_batch(batch.id, db_session, farmer_b)
    with pytest.raises(NotFoundError):
        await update_batch_draft(batch.id, BatchUpdateIn(unit="kg"), db_session, farmer_b)
    with pytest.raises(NotFoundError):
        await submit_batch(batch.id, db_session, farmer_b)
    with pytest.raises(NotFoundError):
        await add_batch_document(
            batch.id,
            BatchDocumentIn(document_type="photo", file_url="https://example.test/x.jpg"),
            db_session,
            farmer_b,
        )

    # farmer_a still can.
    fetched = await get_my_batch(batch.id, db_session, farmer_a)
    assert fetched.id == batch.id


@pytest.mark.asyncio
async def test_staff_permission_gating(db_session):
    farmer = User(firebase_uid="marketplace-farmer-3", status="active")
    owner_user = User(firebase_uid="marketplace-owner-4", status="active")
    field_verifier_user = User(firebase_uid="marketplace-fv-1", status="active")
    qc_user = User(firebase_uid="marketplace-qc-1", status="active")
    db_session.add_all([farmer, owner_user, field_verifier_user, qc_user])
    await db_session.flush()
    owner_ctx = _admin(owner_user, AdminRole.OWNER)
    field_verifier_ctx = _admin(field_verifier_user, AdminRole.FIELD_VERIFIER)
    qc_ctx = _admin(qc_user, AdminRole.QUALITY_CONTROL)

    # Field Verifier and Quality Control cannot manage the catalogue.
    with pytest.raises(ForbiddenError):
        await create_category(
            CategoryIn(slug="oil-cakes", name="Oil cakes"), db_session, field_verifier_ctx
        )
    with pytest.raises(ForbiddenError):
        await create_category(CategoryIn(slug="oil-cakes", name="Oil cakes"), db_session, qc_ctx)

    _category, product_type_id = await _seed_catalog(db_session, owner_ctx)

    await apply_as_supplier(SupplierApplyIn(district="Salem"), db_session, farmer)
    await submit_supplier_profile(db_session, farmer)
    profile = await my_supplier_profile(db_session, farmer)

    # Quality Control cannot decide a supplier application (Field Verifier's job).
    with pytest.raises(ForbiddenError):
        await decide_supplier(
            profile.id, SupplierDecisionIn(status=SupplierStatus.UNDER_REVIEW), db_session, qc_ctx
        )
    # Field Verifier can.
    await decide_supplier(
        profile.id,
        SupplierDecisionIn(status=SupplierStatus.UNDER_REVIEW),
        db_session,
        field_verifier_ctx,
    )


@pytest.mark.asyncio
async def test_new_product_type_request_never_auto_sellable(db_session):
    farmer = User(firebase_uid="marketplace-farmer-4", status="active")
    owner_user = User(firebase_uid="marketplace-owner-5", status="active")
    db_session.add_all([farmer, owner_user])
    await db_session.flush()
    owner_ctx = _admin(owner_user, AdminRole.OWNER)

    request = await submit_new_product_request(
        NewProductTypeRequestIn(proposed_name_en="Biochar mix"), db_session, farmer
    )
    assert request.status == "pending"

    await decide_new_product_request(
        request.id,
        NewProductTypeRequestDecisionIn(
            status=NewProductRequestStatus.APPROVED, review_note="Looks good"
        ),
        db_session,
        owner_ctx,
    )
    # Approval only clears the request queue -- it does not itself create a
    # sellable MarketplaceProductType (an admin still creates that deliberately).
    count = len((await db_session.scalars(select(MarketplaceProductType))).all())
    assert count == 0
