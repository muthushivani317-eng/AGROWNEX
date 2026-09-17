"""Organic Inputs Marketplace procurement + inventory phase: offer, accept/
reject, receipt, and inventory tracking off a received batch.

Covers: an offer can only be made on an approved batch and within its
approved quantity; only the batch's own owner can accept/reject an offer;
a rejected offer is terminal (no renegotiation loop, per BATCH_TRANSITIONS);
receipt requires a real accepted offer and creates the inventory lot with a
correctly-recorded opening RECEIPT movement; inventory movements cannot take
a lot below zero and draining a RELEASED_FOR_SALE lot to zero marks the
batch SOLD_OUT automatically; and staff permission gating for the new
MANAGE_MARKETPLACE_PROCUREMENT permission.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.modules.admin.constants import AdminRole, permissions_for
from app.modules.admin.models import AdminUser
from app.modules.admin.service import AdminContext
from app.modules.auth.models import User
from app.modules.organic_inputs.constants import BatchStatus, CatalogStatus, SupplierStatus
from app.modules.organic_inputs.router import (
    add_batch_test_result,
    apply_as_supplier,
    collect_batch_sample,
    create_batch,
    create_category,
    create_procurement_offer,
    create_product_type,
    decide_batch,
    decide_procurement_offer,
    decide_supplier,
    get_batch_inventory,
    get_procurement_offer,
    list_inventory,
    publish_product_type_version,
    record_batch_inspection,
    record_batch_receipt,
    record_inventory_movement,
    set_product_type_status,
    submit_batch,
    submit_supplier_profile,
    my_supplier_profile,
)
from app.modules.organic_inputs.schemas import (
    BatchCreateIn,
    BatchDecisionIn,
    BatchInspectionIn,
    BatchReceiptIn,
    BatchSampleIn,
    BatchTestResultIn,
    CatalogStatusIn,
    CategoryIn,
    InventoryMovementIn,
    ProcurementOfferDecisionIn,
    ProcurementOfferIn,
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
        CategoryIn(slug="oil-cakes", name="Neem oil cake"), db_session, owner_ctx
    )
    product_type = await create_product_type(
        ProductTypeIn(category_id=category.id, slug="neem-cake", name="Neem cake"),
        db_session,
        owner_ctx,
    )
    product_type_id = uuid.UUID(product_type["id"])
    await publish_product_type_version(
        product_type_id,
        ProductTypeVersionIn(unit_of_measurement="kg", allowed_pack_sizes=["25kg"]),
        db_session,
        owner_ctx,
    )
    await set_product_type_status(
        product_type_id, CatalogStatusIn(status=CatalogStatus.ACTIVE), db_session, owner_ctx
    )
    return product_type_id


async def _approved_batch(db_session, farmer: User, owner_ctx, product_type_id, approved_qty="100"):
    """Drives a fresh batch all the way to APPROVED (the QC happy path)."""
    await apply_as_supplier(SupplierApplyIn(district="Coimbatore"), db_session, farmer)
    await submit_supplier_profile(db_session, farmer)
    profile = await my_supplier_profile(db_session, farmer)
    for target in (
        SupplierStatus.UNDER_REVIEW,
        SupplierStatus.INSPECTION_SCHEDULED,
        SupplierStatus.INSPECTION_COMPLETED,
        SupplierStatus.APPROVED,
    ):
        await decide_supplier(profile.id, SupplierDecisionIn(status=target), db_session, owner_ctx)
    batch = await create_batch(
        BatchCreateIn(product_type_id=product_type_id, batch_quantity="100", unit="kg"),
        db_session,
        farmer,
    )
    await submit_batch(batch.id, db_session, farmer)
    await decide_batch(
        batch.id, BatchDecisionIn(status=BatchStatus.UNDER_REVIEW), db_session, owner_ctx
    )
    await decide_batch(
        batch.id, BatchDecisionIn(status=BatchStatus.INSPECTION_REQUIRED), db_session, owner_ctx
    )
    await record_batch_inspection(
        batch.id, BatchInspectionIn(outcome="passed"), db_session, owner_ctx
    )
    sample = await collect_batch_sample(
        batch.id, BatchSampleIn(quantity="2", unit="kg"), db_session, owner_ctx
    )
    await add_batch_test_result(
        batch.id,
        sample.id,
        BatchTestResultIn(parameter_name="heavy_metals", pass_fail=True),
        db_session,
        owner_ctx,
    )
    await decide_batch(
        batch.id,
        BatchDecisionIn(status=BatchStatus.APPROVED, approved_quantity=approved_qty),
        db_session,
        owner_ctx,
    )
    return batch


@pytest.mark.asyncio
async def test_offer_ceiling_and_batch_status_are_enforced(db_session):
    draft_farmer = User(firebase_uid="proc-farmer-1-draft", status="active")
    farmer = User(firebase_uid="proc-farmer-1", status="active")
    owner_user = User(firebase_uid="proc-owner-1", status="active")
    db_session.add_all([draft_farmer, farmer, owner_user])
    await db_session.flush()
    owner_ctx = _admin(owner_user, AdminRole.OWNER)
    product_type_id = await _seed_catalog(db_session, owner_ctx)

    # Cannot offer on a batch that hasn't even been submitted yet -- needs its
    # own approved-supplier farmer since create_batch requires one, but this
    # batch itself is left in DRAFT (never submitted/reviewed).
    await apply_as_supplier(SupplierApplyIn(district="Coimbatore"), db_session, draft_farmer)
    await submit_supplier_profile(db_session, draft_farmer)
    draft_profile = await my_supplier_profile(db_session, draft_farmer)
    for target in (
        SupplierStatus.UNDER_REVIEW,
        SupplierStatus.INSPECTION_SCHEDULED,
        SupplierStatus.INSPECTION_COMPLETED,
        SupplierStatus.APPROVED,
    ):
        await decide_supplier(
            draft_profile.id, SupplierDecisionIn(status=target), db_session, owner_ctx
        )
    draft_batch = await create_batch(
        BatchCreateIn(product_type_id=product_type_id, batch_quantity="50", unit="kg"),
        db_session,
        draft_farmer,
    )
    with pytest.raises(ConflictError):
        await create_procurement_offer(
            draft_batch.id,
            ProcurementOfferIn(offered_quantity="10", unit="kg", offered_unit_price="20"),
            db_session,
            owner_ctx,
        )

    batch = await _approved_batch(db_session, farmer, owner_ctx, product_type_id, "100")

    # Cannot offer more than what was approved.
    with pytest.raises(ValidationError):
        await create_procurement_offer(
            batch.id,
            ProcurementOfferIn(offered_quantity="150", unit="kg", offered_unit_price="20"),
            db_session,
            owner_ctx,
        )

    offer = await create_procurement_offer(
        batch.id,
        ProcurementOfferIn(offered_quantity="90", unit="kg", offered_unit_price="18.50"),
        db_session,
        owner_ctx,
    )
    assert offer.status == "offered"

    # A second offer on the same batch is rejected -- one offer per batch.
    with pytest.raises(ConflictError):
        await create_procurement_offer(
            batch.id,
            ProcurementOfferIn(offered_quantity="10", unit="kg", offered_unit_price="18.50"),
            db_session,
            owner_ctx,
        )


@pytest.mark.asyncio
async def test_only_batch_owner_can_decide_offer(db_session):
    farmer = User(firebase_uid="proc-farmer-2", status="active")
    other_farmer = User(firebase_uid="proc-farmer-2b", status="active")
    owner_user = User(firebase_uid="proc-owner-2", status="active")
    db_session.add_all([farmer, other_farmer, owner_user])
    await db_session.flush()
    owner_ctx = _admin(owner_user, AdminRole.OWNER)
    product_type_id = await _seed_catalog(db_session, owner_ctx)
    batch = await _approved_batch(db_session, farmer, owner_ctx, product_type_id)
    await create_procurement_offer(
        batch.id,
        ProcurementOfferIn(offered_quantity="50", unit="kg", offered_unit_price="20"),
        db_session,
        owner_ctx,
    )

    with pytest.raises(NotFoundError):
        await decide_procurement_offer(
            batch.id, ProcurementOfferDecisionIn(accept=True), db_session, other_farmer
        )


@pytest.mark.asyncio
async def test_rejected_offer_is_terminal(db_session):
    farmer = User(firebase_uid="proc-farmer-3", status="active")
    owner_user = User(firebase_uid="proc-owner-3", status="active")
    db_session.add_all([farmer, owner_user])
    await db_session.flush()
    owner_ctx = _admin(owner_user, AdminRole.OWNER)
    product_type_id = await _seed_catalog(db_session, owner_ctx)
    batch = await _approved_batch(db_session, farmer, owner_ctx, product_type_id)
    await create_procurement_offer(
        batch.id,
        ProcurementOfferIn(offered_quantity="50", unit="kg", offered_unit_price="20"),
        db_session,
        owner_ctx,
    )

    result = await decide_procurement_offer(
        batch.id,
        ProcurementOfferDecisionIn(accept=False, rejection_reason="Price too low"),
        db_session,
        farmer,
    )
    assert result["status"] == BatchStatus.OFFER_REJECTED.value

    # No re-offer / renegotiation loop -- the batch is no longer APPROVED.
    with pytest.raises(ConflictError):
        await create_procurement_offer(
            batch.id,
            ProcurementOfferIn(offered_quantity="10", unit="kg", offered_unit_price="25"),
            db_session,
            owner_ctx,
        )


@pytest.mark.asyncio
async def test_receipt_requires_accepted_offer_and_creates_inventory(db_session):
    farmer = User(firebase_uid="proc-farmer-4", status="active")
    owner_user = User(firebase_uid="proc-owner-4", status="active")
    db_session.add_all([farmer, owner_user])
    await db_session.flush()
    owner_ctx = _admin(owner_user, AdminRole.OWNER)
    product_type_id = await _seed_catalog(db_session, owner_ctx)
    batch = await _approved_batch(db_session, farmer, owner_ctx, product_type_id, "100")

    # Cannot receive before there's even an offer.
    with pytest.raises(ConflictError):
        await record_batch_receipt(
            batch.id,
            BatchReceiptIn(received_quantity="90", unit="kg"),
            db_session,
            owner_ctx,
        )

    await create_procurement_offer(
        batch.id,
        ProcurementOfferIn(offered_quantity="90", unit="kg", offered_unit_price="18.50"),
        db_session,
        owner_ctx,
    )

    # Cannot receive while the offer is still pending (not yet accepted).
    with pytest.raises(ConflictError):
        await record_batch_receipt(
            batch.id,
            BatchReceiptIn(received_quantity="90", unit="kg"),
            db_session,
            owner_ctx,
        )

    await decide_procurement_offer(
        batch.id, ProcurementOfferDecisionIn(accept=True), db_session, farmer
    )

    # Cannot receive more than what was accepted.
    with pytest.raises(ValidationError):
        await record_batch_receipt(
            batch.id,
            BatchReceiptIn(received_quantity="95", unit="kg"),
            db_session,
            owner_ctx,
        )

    receipt = await record_batch_receipt(
        batch.id,
        BatchReceiptIn(received_quantity="88", unit="kg", condition_note="Minor spillage"),
        db_session,
        owner_ctx,
    )
    assert receipt.received_quantity == Decimal("88")

    lot = await get_batch_inventory(batch.id, db_session, owner_ctx)
    assert lot.quantity_available == Decimal("88")
    assert lot.unit_cost == Decimal("18.50")
    assert len(lot.movements) == 1
    assert lot.movements[0].movement_type == "receipt"

    all_lots = await list_inventory(db_session, owner_ctx, product_type_id=product_type_id)
    assert len(all_lots) == 1


@pytest.mark.asyncio
async def test_inventory_movement_blocks_negative_and_sold_out_is_automatic(db_session):
    farmer = User(firebase_uid="proc-farmer-5", status="active")
    owner_user = User(firebase_uid="proc-owner-5", status="active")
    db_session.add_all([farmer, owner_user])
    await db_session.flush()
    owner_ctx = _admin(owner_user, AdminRole.OWNER)
    product_type_id = await _seed_catalog(db_session, owner_ctx)
    batch = await _approved_batch(db_session, farmer, owner_ctx, product_type_id, "100")
    await create_procurement_offer(
        batch.id,
        ProcurementOfferIn(offered_quantity="50", unit="kg", offered_unit_price="20"),
        db_session,
        owner_ctx,
    )
    await decide_procurement_offer(
        batch.id, ProcurementOfferDecisionIn(accept=True), db_session, farmer
    )
    await record_batch_receipt(
        batch.id, BatchReceiptIn(received_quantity="50", unit="kg"), db_session, owner_ctx
    )
    await decide_batch(
        batch.id, BatchDecisionIn(status=BatchStatus.RELEASED_FOR_SALE), db_session, owner_ctx
    )

    # Cannot withdraw more than what's available.
    with pytest.raises(ValidationError):
        await record_inventory_movement(
            batch.id,
            InventoryMovementIn(movement_type="withdrawal", quantity_delta="-60"),
            db_session,
            owner_ctx,
        )

    await record_inventory_movement(
        batch.id,
        InventoryMovementIn(movement_type="withdrawal", quantity_delta="-30", note="Manual sale"),
        db_session,
        owner_ctx,
    )
    lot = await get_batch_inventory(batch.id, db_session, owner_ctx)
    assert lot.quantity_available == Decimal("20")

    # Draining the lot to zero while RELEASED_FOR_SALE auto-marks SOLD_OUT.
    await record_inventory_movement(
        batch.id,
        InventoryMovementIn(movement_type="withdrawal", quantity_delta="-20"),
        db_session,
        owner_ctx,
    )
    refreshed = await get_batch_inventory(batch.id, db_session, owner_ctx)
    assert refreshed.quantity_available == Decimal("0")

    from app.modules.organic_inputs.models import ProductionBatch

    updated_batch = await db_session.get(ProductionBatch, batch.id)
    assert updated_batch.status == BatchStatus.SOLD_OUT.value


@pytest.mark.asyncio
async def test_procurement_permission_gating(db_session):
    farmer = User(firebase_uid="proc-farmer-6", status="active")
    owner_user = User(firebase_uid="proc-owner-6", status="active")
    fv_user = User(firebase_uid="proc-fv-1", status="active")
    db_session.add_all([farmer, owner_user, fv_user])
    await db_session.flush()
    owner_ctx = _admin(owner_user, AdminRole.OWNER)
    fv_ctx = _admin(fv_user, AdminRole.FIELD_VERIFIER)
    product_type_id = await _seed_catalog(db_session, owner_ctx)
    batch = await _approved_batch(db_session, farmer, owner_ctx, product_type_id)

    # Field Verifier holds MANAGE_MARKETPLACE_SUPPLIERS, not
    # MANAGE_MARKETPLACE_PROCUREMENT -- cannot make a procurement offer.
    with pytest.raises(ForbiddenError):
        await create_procurement_offer(
            batch.id,
            ProcurementOfferIn(offered_quantity="10", unit="kg", offered_unit_price="20"),
            db_session,
            fv_ctx,
        )

    # But Field Verifier CAN still view the batch's (nonexistent) offer/inventory
    # -- view permissions are shared across the marketplace admin roles.
    with pytest.raises(NotFoundError):
        await get_procurement_offer(batch.id, db_session, fv_ctx)
