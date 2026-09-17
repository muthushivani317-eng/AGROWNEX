"""Organic Inputs Marketplace QC phase: inspection, sampling, test results.

Covers: a batch cannot skip inspection/sampling/testing evidence to reach a
sellable status, only recorded evidence can move it forward, staff permission
gating between Field Verifier and Quality Control, and the full happy-path
chain to APPROVED.
"""

from __future__ import annotations

import uuid

import pytest

from app.core.exceptions import ConflictError, ForbiddenError, ValidationError
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
    create_product_type,
    decide_batch,
    decide_supplier,
    publish_product_type_version,
    record_batch_inspection,
    set_product_type_status,
    submit_batch,
    submit_supplier_profile,
    my_supplier_profile,
)
from app.modules.organic_inputs.schemas import (
    BatchCreateIn,
    BatchDecisionIn,
    BatchInspectionIn,
    BatchSampleIn,
    BatchTestResultIn,
    CatalogStatusIn,
    CategoryIn,
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


async def _approved_supplier_batch(db_session, farmer: User, owner_ctx, product_type_id):
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
    return batch


@pytest.mark.asyncio
async def test_batch_cannot_reach_sample_or_testing_without_recorded_evidence(db_session):
    farmer = User(firebase_uid="qc-farmer-1", status="active")
    owner_user = User(firebase_uid="qc-owner-1", status="active")
    db_session.add_all([farmer, owner_user])
    await db_session.flush()
    owner_ctx = _admin(owner_user, AdminRole.OWNER)
    product_type_id = await _seed_catalog(db_session, owner_ctx)
    batch = await _approved_supplier_batch(db_session, farmer, owner_ctx, product_type_id)

    # Cannot jump straight to SAMPLE_COLLECTED/TESTING/APPROVED via decide_batch.
    with pytest.raises(ValidationError):
        await decide_batch(
            batch.id, BatchDecisionIn(status=BatchStatus.SAMPLE_COLLECTED), db_session, owner_ctx
        )
    with pytest.raises(ValidationError):
        await decide_batch(
            batch.id, BatchDecisionIn(status=BatchStatus.APPROVED), db_session, owner_ctx
        )

    # Cannot collect a sample before inspection is recorded.
    with pytest.raises(ConflictError):
        await collect_batch_sample(
            batch.id, BatchSampleIn(quantity="1", unit="kg"), db_session, owner_ctx
        )


@pytest.mark.asyncio
async def test_failed_inspection_rejects_batch(db_session):
    farmer = User(firebase_uid="qc-farmer-2", status="active")
    owner_user = User(firebase_uid="qc-owner-2", status="active")
    db_session.add_all([farmer, owner_user])
    await db_session.flush()
    owner_ctx = _admin(owner_user, AdminRole.OWNER)
    product_type_id = await _seed_catalog(db_session, owner_ctx)
    batch = await _approved_supplier_batch(db_session, farmer, owner_ctx, product_type_id)

    result = await record_batch_inspection(
        batch.id,
        BatchInspectionIn(outcome="failed", findings_note="Contamination found"),
        db_session,
        owner_ctx,
    )
    assert result["status"] == BatchStatus.REJECTED.value

    # A rejected batch cannot then have a sample collected.
    with pytest.raises(ConflictError):
        await collect_batch_sample(batch.id, BatchSampleIn(), db_session, owner_ctx)


@pytest.mark.asyncio
async def test_qc_permission_gating_between_field_verifier_and_quality_control(db_session):
    farmer = User(firebase_uid="qc-farmer-3", status="active")
    owner_user = User(firebase_uid="qc-owner-3", status="active")
    fv_user = User(firebase_uid="qc-fv-1", status="active")
    db_session.add_all([farmer, owner_user, fv_user])
    await db_session.flush()
    owner_ctx = _admin(owner_user, AdminRole.OWNER)
    fv_ctx = _admin(fv_user, AdminRole.FIELD_VERIFIER)
    product_type_id = await _seed_catalog(db_session, owner_ctx)
    batch = await _approved_supplier_batch(db_session, farmer, owner_ctx, product_type_id)

    # Field Verifier CAN record the inspection (site visit is their job).
    result = await record_batch_inspection(
        batch.id,
        BatchInspectionIn(outcome="passed"),
        db_session,
        fv_ctx,
    )
    assert result["status"] == BatchStatus.INSPECTION_COMPLETED.value

    # Field Verifier CANNOT collect a lab sample -- that's Quality Control's job.
    with pytest.raises(ForbiddenError):
        await collect_batch_sample(batch.id, BatchSampleIn(), db_session, fv_ctx)


@pytest.mark.asyncio
async def test_full_qc_happy_path_reaches_approved(db_session):
    farmer = User(firebase_uid="qc-farmer-4", status="active")
    owner_user = User(firebase_uid="qc-owner-4", status="active")
    qc_user = User(firebase_uid="qc-qc-1", status="active")
    db_session.add_all([farmer, owner_user, qc_user])
    await db_session.flush()
    owner_ctx = _admin(owner_user, AdminRole.OWNER)
    qc_ctx = _admin(qc_user, AdminRole.QUALITY_CONTROL)
    product_type_id = await _seed_catalog(db_session, owner_ctx)
    batch = await _approved_supplier_batch(db_session, farmer, owner_ctx, product_type_id)

    await record_batch_inspection(
        batch.id, BatchInspectionIn(outcome="passed"), db_session, owner_ctx
    )
    sample = await collect_batch_sample(
        batch.id,
        BatchSampleIn(quantity="2", unit="kg"),
        db_session,
        qc_ctx,
    )

    # Cannot decide the testing outcome before it's even reached TESTING.
    with pytest.raises(ValidationError):
        await decide_batch(
            batch.id, BatchDecisionIn(status=BatchStatus.APPROVED), db_session, owner_ctx
        )

    result = await add_batch_test_result(
        batch.id,
        sample.id,
        BatchTestResultIn(parameter_name="heavy_metals", pass_fail=True, lab_name="Test Labs"),
        db_session,
        qc_ctx,
    )
    assert result.pass_fail is True

    decision = await decide_batch(
        batch.id,
        BatchDecisionIn(status=BatchStatus.APPROVED, approved_quantity="100"),
        db_session,
        owner_ctx,
    )
    assert decision["status"] == BatchStatus.APPROVED.value


@pytest.mark.asyncio
async def test_cannot_add_test_result_to_another_batchs_sample(db_session):
    farmer_a = User(firebase_uid="qc-farmer-5a", status="active")
    farmer_b = User(firebase_uid="qc-farmer-5b", status="active")
    owner_user = User(firebase_uid="qc-owner-5", status="active")
    qc_user = User(firebase_uid="qc-qc-2", status="active")
    db_session.add_all([farmer_a, farmer_b, owner_user, qc_user])
    await db_session.flush()
    owner_ctx = _admin(owner_user, AdminRole.OWNER)
    qc_ctx = _admin(qc_user, AdminRole.QUALITY_CONTROL)
    product_type_id = await _seed_catalog(db_session, owner_ctx)

    batch_a = await _approved_supplier_batch(db_session, farmer_a, owner_ctx, product_type_id)
    batch_b = await _approved_supplier_batch(db_session, farmer_b, owner_ctx, product_type_id)

    await record_batch_inspection(
        batch_a.id, BatchInspectionIn(outcome="passed"), db_session, owner_ctx
    )
    sample_a = await collect_batch_sample(batch_a.id, BatchSampleIn(), db_session, qc_ctx)

    from app.core.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        await add_batch_test_result(
            batch_b.id,
            sample_a.id,
            BatchTestResultIn(parameter_name="moisture", pass_fail=True),
            db_session,
            qc_ctx,
        )
