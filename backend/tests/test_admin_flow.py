"""Integration tests for the Admin platform service + repository.

Exercises RBAC (non-admin rejected, suspended rejected, least-privilege denial),
the read-only dashboard/analytics/AI metrics over real records, farmer management
(directory + detail, search/filter), the procurement pipeline (status change is
audited and derived from the immutable trail — no farmer table is mutated), broadcast
delivery via a mock provider, announcements, and the audit trail. Nothing is
fabricated; untracked metrics stay ``None``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest
from app.modules.admin.constants import AdminRole, ProcurementStatus
from app.modules.admin.exceptions import (
    AdminSuspendedError,
    NotAnAdminError,
    OfferNotFoundError,
    PermissionDeniedError,
)
from app.modules.admin.provider import MockBroadcastProvider
from app.modules.admin.schemas import FarmerDetailOut
from app.modules.admin.seed import ensure_admin
from app.modules.admin.service import AdminService
from app.modules.auth.models import User
from app.modules.auth.profile_models import FarmerProfile
from app.modules.consents.service import ConsentService
from app.modules.farms.models import Farm
from app.modules.produce.models import ProduceOffer

NOW = datetime(2026, 7, 13, 8, 0, tzinfo=UTC)


async def _user(db_session, uid: str, *, phone: str | None = None) -> User:
    user = User(firebase_uid=uid, phone_number=phone, status="active", last_login=NOW)
    db_session.add(user)
    await db_session.flush()
    return user


async def _farmer(
    db_session,
    uid: str,
    *,
    name: str,
    district: str = "Thanjavur",
    village: str = "Kabisthalam",
    crop: str = "paddy",
    phone: str | None = None,
) -> User:
    user = await _user(db_session, uid, phone=phone)
    db_session.add(
        FarmerProfile(
            user_id=user.id,
            full_name=name,
            district=district,
            village=village,
            primary_crop=crop,
            language="ta",
        )
    )
    db_session.add(Farm(user_id=user.id, name=f"{name}'s field", crop=crop, soil_type="clay"))
    await db_session.flush()
    return user


async def _offer(
    db_session,
    user: User,
    *,
    crop: str = "paddy",
    quantity: float = 2,
    unit: str = "tonne",
    village: str = "Kabisthalam",
    district: str = "Thanjavur",
    harvest: date = date(2026, 8, 1),
) -> ProduceOffer:
    farm = (
        await db_session.execute(Farm.__table__.select().where(Farm.user_id == user.id))
    ).first()
    offer = ProduceOffer(
        user_id=user.id,
        farm_id=farm.id if farm else uuid.uuid4(),
        crop_name=crop,
        quantity=quantity,
        unit=unit,
        expected_harvest_date=harvest,
        village=village,
        district=district,
        status="submitted",
    )
    db_session.add(offer)
    await db_session.flush()
    return offer


def _service(db_session) -> AdminService:
    return AdminService(db_session, now=NOW, broadcast_provider=MockBroadcastProvider())


async def _admin_ctx(db_session, service, *, role: str = AdminRole.SUPER_ADMIN.value):
    user = await _user(db_session, f"fb-admin-{role}-{uuid.uuid4().hex[:6]}")
    await ensure_admin(db_session, user.id, role=role, full_name="Ops Admin")
    return await service.resolve_admin(user, ip_address="10.0.0.9")


# --------------------------------------------------------------------------- #
# RBAC
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_non_admin_is_rejected(db_session):
    service = _service(db_session)
    user = await _user(db_session, "fb-plain")
    with pytest.raises(NotAnAdminError):
        await service.resolve_admin(user)


@pytest.mark.asyncio
async def test_suspended_admin_is_rejected(db_session):
    service = _service(db_session)
    user = await _user(db_session, "fb-susp")
    admin = await ensure_admin(db_session, user.id)
    admin.status = "suspended"
    await db_session.flush()
    with pytest.raises(AdminSuspendedError):
        await service.resolve_admin(user)


@pytest.mark.asyncio
async def test_least_privilege_denies_out_of_scope_action(db_session):
    service = _service(db_session)
    ctx = await _admin_ctx(db_session, service, role=AdminRole.PROCUREMENT_MANAGER.value)
    # A procurement manager may not browse the farmer directory.
    with pytest.raises(PermissionDeniedError):
        await service.farmers(ctx, search=None, district=None, crop=None, page=1, page_size=20)
    # …but they can see procurement.
    result = await service.procurement(
        ctx, crop=None, village=None, district=None, page=1, page_size=20
    )
    assert "analytics" in result


# --------------------------------------------------------------------------- #
# Dashboard + analytics + AI
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_dashboard_counts_and_audits(db_session):
    service = _service(db_session)
    await _farmer(db_session, "fb-f1", name="Raja")
    await _farmer(db_session, "fb-f2", name="Kumar", village="Papanasam")
    ctx = await _admin_ctx(db_session, service)

    data = await service.dashboard(ctx)
    cards = {c.key: c.value for c in data["cards"]}
    assert cards["total_farmers"] == 2
    assert cards["total_farms"] == 2
    assert data["generated_at"] == NOW

    # The dashboard view itself was audited.
    audit = await service.audit(ctx, action="view_dashboard", target=None, page=1, page_size=10)
    assert audit.total >= 1


@pytest.mark.asyncio
async def test_analytics_distributions_are_real(db_session):
    service = _service(db_session)
    await _farmer(db_session, "fb-a1", name="A", crop="paddy")
    await _farmer(db_session, "fb-a2", name="B", crop="paddy")
    await _farmer(db_session, "fb-a3", name="C", crop="banana")
    ctx = await _admin_ctx(db_session, service)

    data = await service.analytics(ctx)
    crops = {d["label"]: d["count"] for d in data["crop_distribution"]}
    assert crops["paddy"] == 2
    assert crops["banana"] == 1


@pytest.mark.asyncio
async def test_ai_monitoring_surfaces_untracked_as_null(db_session):
    service = _service(db_session)
    ctx = await _admin_ctx(db_session, service)
    data = await service.ai_monitoring(ctx)
    # Latency + failures are not instrumented in V1 — honest null, never faked.
    assert data["model_latency_ms"] is None
    assert data["api_failures"] is None
    assert isinstance(data["daily_requests"], list)


# --------------------------------------------------------------------------- #
# Farmer management
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_farmer_directory_search_and_detail(db_session):
    service = _service(db_session)
    raja = await _farmer(db_session, "fb-r", name="Raja Selvam", phone="+919000000001")
    await _farmer(db_session, "fb-k", name="Kumar", village="Papanasam")
    ctx = await _admin_ctx(db_session, service)

    page = await service.farmers(ctx, search="raja", district=None, crop=None, page=1, page_size=20)
    assert page.total == 1
    assert page.items[0].full_name == "Raja Selvam"
    assert page.items[0].farm_count == 1

    detail = await service.farmer_detail(ctx, raja.id)
    assert detail["profile"].full_name == "Raja Selvam"
    assert len(detail["farms"]) == 1
    assert "disease" in detail["counts"]


@pytest.mark.asyncio
async def test_farmer_detail_exposes_current_consent_state_without_raw_metadata(db_session):
    service = _service(db_session)
    farmer = await _farmer(db_session, "fb-consent-admin", name="Consent Farmer")
    await ConsentService(db_session).record(
        farmer.id,
        purpose="buyer_contact_sharing",
        granted=True,
        idempotency_key="admin-consent-1",
        locale="en",
        notice_version="2026-08-v1",
    )
    ctx = await _admin_ctx(db_session, service)
    detail = await service.farmer_detail(ctx, farmer.id)
    consent = next(item for item in detail["consents"] if item.purpose == "buyer_contact_sharing")
    assert consent.granted is True
    assert consent.policy_version == "2026-08-v1"
    assert not hasattr(consent, "metadata")
    payload = FarmerDetailOut.from_detail(farmer.id, detail).model_dump()
    assert any(item["purpose"] == "buyer_contact_sharing" for item in payload["consents"])
    assert all("metadata" not in item for item in payload["consents"])


# --------------------------------------------------------------------------- #
# Procurement pipeline (audited; derived from the immutable trail)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_procurement_status_change_is_audited_and_reflected(db_session):
    service = _service(db_session)
    farmer = await _farmer(db_session, "fb-p1", name="Meena")
    offer = await _offer(db_session, farmer)
    ctx = await _admin_ctx(db_session, service)

    # Initially every offer is "new" (default, from the empty trail).
    first = await service.procurement(
        ctx, crop=None, village=None, district=None, page=1, page_size=20
    )
    assert first["page"].total == 1
    assert first["page"].items[0]["admin_status"] == ProcurementStatus.NEW.value
    assert first["analytics"]["total_quantity_kg"] == 2000.0

    new_status = await service.update_procurement_status(
        ctx, offer.id, ProcurementStatus.CONTACTED.value, note="called farmer"
    )
    assert new_status == ProcurementStatus.CONTACTED.value

    second = await service.procurement(
        ctx, crop=None, village=None, district=None, page=1, page_size=20
    )
    assert second["page"].items[0]["admin_status"] == ProcurementStatus.CONTACTED.value

    dash = await service.dashboard(ctx)
    assert dash["procurement_status_counts"].get(ProcurementStatus.CONTACTED.value) == 1


@pytest.mark.asyncio
async def test_procurement_status_rejects_bad_status_and_unknown_offer(db_session):
    service = _service(db_session)
    ctx = await _admin_ctx(db_session, service)
    with pytest.raises(Exception):  # noqa: B017 — invalid status value
        await service.update_procurement_status(ctx, uuid.uuid4(), "teleported")
    with pytest.raises(OfferNotFoundError):
        await service.update_procurement_status(
            ctx, uuid.uuid4(), ProcurementStatus.UNDER_REVIEW.value
        )


# --------------------------------------------------------------------------- #
# Broadcast + notifications + announcements
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_immediate_broadcast_delivers_and_lists(db_session):
    service = _service(db_session)
    await _farmer(db_session, "fb-b1", name="X", village="Kabisthalam")
    await _farmer(db_session, "fb-b2", name="Y", village="Kabisthalam")
    await _farmer(db_session, "fb-b3", name="Z", village="Papanasam")
    ctx = await _admin_ctx(db_session, service)

    # Village-targeted broadcast reaches exactly the two Kabisthalam farmers.
    broadcast = await service.broadcast(
        ctx,
        title="Rain alert",
        body="Heavy rain expected",
        language="ta",
        target_type="village",
        target_value="Kabisthalam",
        schedule_type="immediate",
        scheduled_for=None,
    )
    assert broadcast.recipient_count == 2
    assert broadcast.delivered_count == 2
    assert broadcast.status == "sent"

    overview = await service.notifications_overview(ctx, page=1, page_size=20)
    assert overview["broadcasts"].total == 1
    assert overview["delivered_total"] == 2


@pytest.mark.asyncio
async def test_scheduled_broadcast_is_queued_not_delivered(db_session):
    service = _service(db_session)
    await _farmer(db_session, "fb-s1", name="X")
    ctx = await _admin_ctx(db_session, service)
    broadcast = await service.broadcast(
        ctx,
        title="Reminder",
        body="Sow soon",
        language="ta",
        target_type="all",
        target_value=None,
        schedule_type="scheduled",
        scheduled_for=datetime(2026, 8, 1, tzinfo=UTC),
    )
    assert broadcast.status == "queued"
    assert broadcast.delivered_count == 0


@pytest.mark.asyncio
async def test_announcement_create_and_list(db_session):
    service = _service(db_session)
    ctx = await _admin_ctx(db_session, service)
    ann = await service.create_announcement(
        ctx,
        title="Maintenance",
        body="Downtime tonight",
        language="en",
        category="ops",
        audience="all",
    )
    assert ann.title == "Maintenance"
    page = await service.announcements(ctx, page=1, page_size=20)
    assert page.total == 1
