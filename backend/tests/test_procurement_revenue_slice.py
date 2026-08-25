from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from app.modules.admin.constants import AdminRole, AuditAction, ProcurementStatus
from app.modules.admin.exceptions import InvalidProcurementStatusError, PermissionDeniedError
from app.modules.admin.models import AuditLog
from app.modules.admin.repository import AdminRepository
from app.modules.admin.schemas import ProcurementCaseUpdateIn
from app.modules.admin.seed import ensure_admin
from app.modules.admin.service import AdminService
from app.modules.auth.models import User
from app.modules.farms.models import Farm
from app.modules.produce.constants import QuantityProvenance
from app.modules.produce.provider import MockProduceProvider
from app.modules.produce.schemas import ProduceOfferCreate, ProduceOfferDetailOut
from app.modules.produce.service import ProduceService
from pydantic import ValidationError

TODAY = date(2026, 8, 25)


async def _user(db, uid: str) -> User:
    user = User(firebase_uid=uid, status="active")
    db.add(user)
    await db.flush()
    return user


async def _farm(db, user: User) -> Farm:
    farm = Farm(user_id=user.id, name="Revenue field", crop="Paddy")
    db.add(farm)
    await db.flush()
    return farm


def _payload(farm_id, **changes) -> ProduceOfferCreate:
    values = dict(
        farm_id=farm_id,
        crop_name="Paddy",
        quantity=20,
        unit="quintal",
        expected_harvest_date=TODAY + timedelta(days=14),
    )
    values.update(changes)
    return ProduceOfferCreate(**values)


async def _admin_ctx(db, service: AdminService, *, role: str):
    user = await _user(db, f"admin-{role}")
    await ensure_admin(db, user.id, role=role, full_name="Team member")
    return await service.resolve_admin(user, ip_address="127.0.0.1")


def test_enriched_offer_validation_and_available_boundary():
    enriched = _payload(
        "00000000-0000-0000-0000-000000000001",
        cultivated_area_hectares=1.5,
        expected_total_quantity=30,
        available_quantity=20,
        quantity_provenance=QuantityProvenance.FARMER_REPORTED,
        quality_notes="Clean and dry",
    )
    assert enriched.available_quantity == 20
    with pytest.raises(ValidationError):
        _payload(
            "00000000-0000-0000-0000-000000000001",
            expected_total_quantity=10,
            available_quantity=11,
        )
    for field in ("cultivated_area_hectares", "expected_total_quantity", "available_quantity"):
        with pytest.raises(ValidationError):
            _payload("00000000-0000-0000-0000-000000000001", **{field: 0})


@pytest.mark.asyncio
async def test_enriched_offer_persists_and_legacy_payload_remains_valid(db_session):
    farmer = await _user(db_session, "farmer-enriched")
    farm = await _farm(db_session, farmer)
    service = ProduceService(db_session, provider=MockProduceProvider(), today=TODAY)
    legacy = await service.create_offer(farmer, _payload(farm.id))
    assert legacy.quantity == 20
    assert legacy.available_quantity is None
    enriched = await service.create_offer(
        farmer,
        _payload(
            farm.id,
            cultivated_area_hectares=2,
            expected_total_quantity=30,
            available_quantity=25,
            quantity_provenance="farmer_reported",
            quality_notes="Grade checked by field team",
        ),
    )
    assert enriched.cultivated_area_hectares == 2
    assert enriched.quantity_provenance == "farmer_reported"


@pytest.mark.parametrize("provenance", ["verified", "system_estimated"])
def test_farmer_offer_rejects_non_farmer_quantity_provenance(provenance):
    with pytest.raises(ValidationError):
        _payload("00000000-0000-0000-0000-000000000001", quantity_provenance=provenance)


@pytest.mark.asyncio
async def test_admin_case_update_is_rbac_guarded_and_internal_fields_never_leak(db_session):
    farmer = await _user(db_session, "farmer-case")
    farm = await _farm(db_session, farmer)
    produce = ProduceService(db_session, provider=MockProduceProvider(), today=TODAY)
    offer = await produce.create_offer(farmer, _payload(farm.id))
    admin = AdminService(db_session, now=datetime(2026, 8, 25, tzinfo=UTC))
    manager = await _admin_ctx(db_session, admin, role=AdminRole.PROCUREMENT_MANAGER.value)
    case = await admin.update_procurement_case(
        manager,
        offer.id,
        ProcurementCaseUpdateIn(
            status=ProcurementStatus.UNDER_REVIEW,
            assigned_admin_id=manager.admin.id,
            buyer_name="Thanjavur Foods",
            buyer_contact="+919999999999",
            buyer_offer_quantity=10,
            buyer_offer_price=2200,
            transport_cost=500,
            commission_rate=2.5,
            negotiation_notes="Internal negotiation only",
        ),
    )
    assert case.status == ProcurementStatus.UNDER_REVIEW.value
    assert case.earned_commission is None
    loaded_offer, _ = await produce.get_offer(farmer, offer.id)
    payload = ProduceOfferDetailOut.from_offer_detail(loaded_offer).model_dump()
    assert "buyer_contact" not in payload
    assert "negotiation_notes" not in payload

    support = await _admin_ctx(db_session, admin, role=AdminRole.CUSTOMER_SUPPORT.value)
    with pytest.raises(PermissionDeniedError):
        await admin.update_procurement_case(
            support, offer.id, ProcurementCaseUpdateIn(status=ProcurementStatus.FINDING_BUYERS)
        )


@pytest.mark.asyncio
async def test_procurement_case_rejects_invalid_status_transition(db_session):
    farmer = await _user(db_session, "farmer-transition")
    farm = await _farm(db_session, farmer)
    offer = await ProduceService(
        db_session, provider=MockProduceProvider(), today=TODAY
    ).create_offer(farmer, _payload(farm.id))
    service = AdminService(db_session, now=datetime(2026, 8, 25, tzinfo=UTC))
    ctx = await _admin_ctx(db_session, service, role=AdminRole.PROCUREMENT_MANAGER.value)
    with pytest.raises((InvalidProcurementStatusError, ValidationError)):
        await service.update_procurement_case(ctx, offer.id, ProcurementCaseUpdateIn(status="sold"))


def test_phase_one_does_not_expose_sale_or_payment_statuses():
    values = {status.value for status in ProcurementStatus}
    assert values == {
        "new",
        "under_review",
        "farmer_contacted",
        "finding_buyers",
        "buyer_interested",
        "offer_received",
        "farmer_approval_pending",
        "cancelled",
    }
    assert "farmer_accepted_at" not in ProcurementCaseUpdateIn.model_fields
    assert "pickup_at" not in ProcurementCaseUpdateIn.model_fields


@pytest.mark.parametrize("legacy", ["confirmed", "collected"])
@pytest.mark.asyncio
async def test_retired_legacy_transitions_fail_cleanly(db_session, legacy):
    service = AdminService(db_session, now=datetime(2026, 8, 25, tzinfo=UTC))
    ctx = await _admin_ctx(db_session, service, role=AdminRole.PROCUREMENT_MANAGER.value)
    with pytest.raises(InvalidProcurementStatusError, match="retired"):
        await service.update_procurement_status(ctx, uuid.uuid4(), legacy)


@pytest.mark.asyncio
async def test_district_manager_cannot_manage_procurement(db_session):
    farmer = await _user(db_session, "farmer-district-denied")
    farm = await _farm(db_session, farmer)
    offer = await ProduceService(
        db_session, provider=MockProduceProvider(), today=TODAY
    ).create_offer(farmer, _payload(farm.id))
    service = AdminService(db_session, now=datetime(2026, 8, 25, tzinfo=UTC))
    ctx = await _admin_ctx(db_session, service, role=AdminRole.DISTRICT_MANAGER.value)
    with pytest.raises(PermissionDeniedError):
        await service.update_procurement_case(
            ctx, offer.id, ProcurementCaseUpdateIn(status=ProcurementStatus.UNDER_REVIEW)
        )


@pytest.mark.asyncio
async def test_legacy_audit_state_initializes_case_and_is_counted_as_fallback(db_session):
    farmer = await _user(db_session, "farmer-legacy-state")
    farm = await _farm(db_session, farmer)
    offer = await ProduceService(
        db_session, provider=MockProduceProvider(), today=TODAY
    ).create_offer(farmer, _payload(farm.id))
    db_session.add(
        AuditLog(
            action=AuditAction.PROCUREMENT_STATUS_CHANGED.value,
            target="procurement",
            target_id=str(offer.id),
            meta={"status": "contacted"},
        )
    )
    await db_session.flush()
    counts = await AdminRepository(db_session).procurement_status_counts()
    assert counts[ProcurementStatus.FARMER_CONTACTED.value] == 1
    service = AdminService(db_session, now=datetime(2026, 8, 25, tzinfo=UTC))
    ctx = await _admin_ctx(db_session, service, role=AdminRole.PROCUREMENT_MANAGER.value)
    case = await service.update_procurement_case(
        ctx, offer.id, ProcurementCaseUpdateIn(status=ProcurementStatus.FINDING_BUYERS)
    )
    assert case.status == ProcurementStatus.FINDING_BUYERS.value


@pytest.mark.asyncio
async def test_procurement_transition_prerequisites_and_decimal_fields(db_session):
    farmer = await _user(db_session, "farmer-prereqs")
    farm = await _farm(db_session, farmer)
    offer = await ProduceService(
        db_session, provider=MockProduceProvider(), today=TODAY
    ).create_offer(farmer, _payload(farm.id, available_quantity=10))
    service = AdminService(db_session, now=datetime(2026, 8, 25, tzinfo=UTC))
    ctx = await _admin_ctx(db_session, service, role=AdminRole.PROCUREMENT_MANAGER.value)
    await service.update_procurement_case(
        ctx, offer.id, ProcurementCaseUpdateIn(status=ProcurementStatus.FARMER_CONTACTED)
    )
    await service.update_procurement_case(
        ctx, offer.id, ProcurementCaseUpdateIn(status=ProcurementStatus.FINDING_BUYERS)
    )
    with pytest.raises(Exception, match="buyer identity"):
        await service.update_procurement_case(
            ctx, offer.id, ProcurementCaseUpdateIn(status=ProcurementStatus.BUYER_INTERESTED)
        )
    await service.update_procurement_case(
        ctx,
        offer.id,
        ProcurementCaseUpdateIn(status=ProcurementStatus.BUYER_INTERESTED, buyer_name="Buyer Ltd"),
    )
    with pytest.raises(Exception, match="available"):
        await service.update_procurement_case(
            ctx,
            offer.id,
            ProcurementCaseUpdateIn(
                status=ProcurementStatus.OFFER_RECEIVED,
                buyer_offer_quantity=Decimal("11"),
                buyer_offer_price=Decimal("2200.50"),
                currency="INR",
                price_unit="quintal",
            ),
        )


def test_procurement_offer_price_must_be_positive():
    with pytest.raises(ValidationError):
        ProcurementCaseUpdateIn(buyer_offer_price=Decimal("0"))
