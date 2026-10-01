"""FPO Crop Board: aggregation correctness and FPO isolation."""
from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.core.exceptions import ForbiddenError, NotFoundError
from app.modules.admin.constants import AdminRole, permissions_for
from app.modules.admin.models import AdminUser
from app.modules.admin.service import AdminContext
from app.modules.auth.models import User
from app.modules.auth.profile_models import FarmerProfile
from app.modules.farms.models import Farm, FarmLocation
from app.modules.fpo_board.router import (
    feed_board,
    list_organizations,
    organization_board,
    organization_farmer_csv,
    organization_farmer_list,
)
from app.modules.fpo_board.service import build_board, farmer_rows
from app.modules.organic_inputs.models import (
    MarketplaceCategory as Category,
)
from app.modules.organic_inputs.models import (
    MarketplaceProductType as ProductType,
)
from app.modules.organic_inputs.models import (
    ProductionBatch,
    ProductTypeVersion,
    SupplierProfile,
)
from app.modules.organic_mvp.models import OrganicFpo
from app.modules.organic_mvp.partner_api_auth import PartnerApiKeyContext
from app.modules.organic_mvp.partner_router import (
    LinkRequestIn,
    OrganizationIn,
    StaffIn,
    add_staff,
    approve_farmer_link,
    create_organization,
    request_farmer_link,
)
from app.modules.produce.models import ProduceOffer

TODAY = date.today()


async def _admin(db_session, role: str, user: User | None = None) -> AdminContext:
    if user is None:
        user = User(firebase_uid=f"admin-{uuid.uuid4()}", status="active")
        db_session.add(user)
        await db_session.flush()
    admin = AdminUser(user_id=user.id, role=role)
    db_session.add(admin)
    await db_session.flush()
    return AdminContext(admin=admin, permissions=frozenset(permissions_for(role)))


async def _org(db_session, platform, name: str):
    fpo = OrganicFpo(name=name, district="Thoothukudi", is_test=True)
    db_session.add(fpo)
    await db_session.flush()
    org = await create_organization(OrganizationIn(name=name, kind="fpo", fpo_id=fpo.id, is_test=True), db_session, platform)
    org_id = uuid.UUID(org["id"])
    manager = User(firebase_uid=f"{name}-manager", status="active")
    db_session.add(manager)
    await db_session.flush()
    await add_staff(org_id, StaffIn(user_id=manager.id, role="manager"), db_session, platform)
    return org_id, manager


async def _farmer(db_session, org_id, manager, *, uid, name, crop, hectares, village, phone):
    farmer = User(firebase_uid=uid, status="active", phone_number=phone)
    db_session.add(farmer)
    await db_session.flush()
    db_session.add(FarmerProfile(user_id=farmer.id, full_name=name, village=village, district="Thoothukudi"))
    farm = Farm(user_id=farmer.id, name=f"{name} farm", crop=crop, area_hectares=hectares)
    db_session.add(farm)
    await db_session.flush()
    db_session.add(FarmLocation(farm_id=farm.id, village=village, district="Thoothukudi"))
    await db_session.flush()
    link = await request_farmer_link(org_id, LinkRequestIn(farmer_ref=farmer.farmer_ref), db_session, manager)
    await approve_farmer_link(link["id"], db_session, farmer)
    return farmer, farm


def _offer(farmer, farm, *, crop, qty, unit="kg", days=None, status="submitted", availability="upcoming_harvest"):
    return ProduceOffer(
        listing_ref=f"L-{uuid.uuid4().hex[:10]}",
        user_id=farmer.id,
        farm_id=farm.id,
        crop_name=crop,
        quantity=qty,
        unit=unit,
        expected_harvest_date=TODAY + timedelta(days=days) if days is not None else None,
        product_category="vegetables",
        availability_type=availability,
        status=status,
    )


async def _vermicompost_batch(db_session, farmer, qty):
    category = Category(slug=f"solid-{uuid.uuid4().hex[:6]}", name="Solid inputs", status="active")
    db_session.add(category)
    await db_session.flush()
    product_type = ProductType(category_id=category.id, slug=f"vermi-{uuid.uuid4().hex[:6]}", name="Vermicompost", status="active")
    db_session.add(product_type)
    await db_session.flush()
    version = ProductTypeVersion(product_type_id=product_type.id, version=1, unit_of_measurement="kg")
    supplier = SupplierProfile(user_id=farmer.id, status="approved")
    db_session.add_all([version, supplier])
    await db_session.flush()
    db_session.add(
        ProductionBatch(
            batch_code=f"PB-{uuid.uuid4().hex[:10]}",
            supplier_id=supplier.id,
            product_type_id=product_type.id,
            product_type_version_id=version.id,
            status="submitted",
            batch_quantity=Decimal(qty),
            unit="kg",
        )
    )
    await db_session.flush()


async def _setup(db_session):
    platform = await _admin(db_session, AdminRole.OWNER.value)
    org_a, manager_a = await _org(db_session, platform, "FPO Alpha")
    org_b, manager_b = await _org(db_session, platform, "FPO Beta")
    raja, raja_farm = await _farmer(db_session, org_a, manager_a, uid="raja", name="Raja", crop="tomato", hectares=1.0, village="Kovil", phone="+919000000001")
    mani, mani_farm = await _farmer(db_session, org_a, manager_a, uid="mani", name="Mani", crop="Tomato", hectares=0.5, village="Pudur", phone="+919000000002")
    _other, _ = await _farmer(db_session, org_b, manager_b, uid="other", name="Other", crop="paddy", hectares=2.0, village="Far", phone="+919000000003")
    db_session.add_all(
        [
            _offer(raja, raja_farm, crop="Tomato", qty=500, days=20),
            _offer(mani, mani_farm, crop="Tomato", qty=300, days=75),
            _offer(mani, mani_farm, crop="Tomato", qty=100, status="withdrawn", days=10),
        ]
    )
    await _vermicompost_batch(db_session, raja, 200)
    await db_session.commit()
    return platform, org_a, org_b, manager_a, raja


@pytest.mark.asyncio
async def test_board_aggregates_crops_harvest_windows_and_products(db_session):
    _, org_a, _, _, _ = await _setup(db_session)
    board = await build_board(db_session, org_a, today=TODAY)

    assert board["summary"]["farmer_count"] == 2
    [tomato] = board["crops"]
    assert tomato["crop"] == "Tomato" and tomato["farmer_count"] == 2 and tomato["farm_count"] == 2
    assert tomato["area_acres"] == pytest.approx(3.71, abs=0.01)
    assert {v["village"] for v in tomato["villages"]} == {"Kovil", "Pudur"}
    assert tomato["expected_harvest"]["within_30_days"] == {"farmer_count": 1, "quantity": {"kg": 500.0}}
    assert tomato["expected_harvest"]["within_90_days"] == {"farmer_count": 2, "quantity": {"kg": 800.0}}

    products = {p["name"]: p for p in board["products"]}
    assert products["Tomato"]["total_quantity"] == 800.0  # withdrawn listing excluded
    assert products["Vermicompost"]["source"] == "organic_input"
    assert products["Vermicompost"]["total_quantity"] == 200.0


@pytest.mark.asyncio
async def test_farmer_rows_filter_by_crop_and_product(db_session):
    _, org_a, _, _, raja = await _setup(db_session)
    rows = await farmer_rows(db_session, org_a, product="vermicompost")
    assert [r["farmer_ref"] for r in rows] == [raja.farmer_ref]
    assert rows[0]["name"] == "Raja" and rows[0]["phone"] == "+919000000001"
    assert len(await farmer_rows(db_session, org_a, crop="tomato")) == 2
    assert await farmer_rows(db_session, org_a, crop="paddy") == []


@pytest.mark.asyncio
async def test_fpo_partner_admin_sees_only_own_organization(db_session):
    platform, org_a, org_b, manager_a, _ = await _setup(db_session)
    fpo_admin = await _admin(db_session, AdminRole.FPO_PARTNER.value, user=manager_a)

    assert [o["id"] for o in await list_organizations(db_session, fpo_admin)] == [str(org_a)]
    board = await organization_board(org_a, db_session, fpo_admin)
    assert board["organization"]["name"] == "FPO Alpha"
    with pytest.raises(NotFoundError):
        await organization_board(org_b, db_session, fpo_admin)
    with pytest.raises(NotFoundError):
        await organization_farmer_list(org_b, db_session, fpo_admin)

    # Platform admin sees both.
    assert len(await list_organizations(db_session, platform)) == 2

    csv_response = await organization_farmer_csv(org_a, db_session, fpo_admin)
    body = csv_response.body.decode()
    assert body.splitlines()[0].startswith("farmer_ref,name,phone")
    assert "Raja" in body and "Other" not in body


@pytest.mark.asyncio
async def test_admin_without_permission_is_refused(db_session):
    _, org_a, _, _, _ = await _setup(db_session)
    support = await _admin(db_session, AdminRole.CUSTOMER_SUPPORT.value)
    with pytest.raises(ForbiddenError):
        await organization_board(org_a, db_session, support)


@pytest.mark.asyncio
async def test_partner_feed_board_is_scoped_to_key_organization(db_session):
    _, org_a, org_b, _, _ = await _setup(db_session)
    board_b = await feed_board(db_session, PartnerApiKeyContext(organization_id=org_b, organization_name="FPO Beta", key_id=uuid.uuid4()))
    assert [c["crop"] for c in board_b["crops"]] == ["Paddy"]
    assert board_b["products"] == []


@pytest.mark.asyncio
async def test_manager_adds_farmer_by_id_and_board_waits_for_consent(db_session):
    from app.modules.fpo_board.router import create_link_request, list_link_requests

    platform, org_a, _, manager_a, _ = await _setup(db_session)
    newcomer = User(firebase_uid="newcomer", status="active")
    db_session.add(newcomer)
    await db_session.flush()
    db_session.add(Farm(user_id=newcomer.id, name="new farm", crop="brinjal", area_hectares=0.4))
    await db_session.commit()

    fpo_manager = await _admin(db_session, AdminRole.FPO_PARTNER.value, user=manager_a)
    result = await create_link_request(org_a, LinkRequestIn(farmer_ref=newcomer.farmer_ref.lower()), db_session, fpo_manager)
    assert result["status"] == "pending"
    requests = await list_link_requests(org_a, db_session, fpo_manager)
    assert {r["farmer_ref"]: r["status"] for r in requests}[newcomer.farmer_ref] == "pending"

    # Not on the board until the farmer approves.
    board = await build_board(db_session, org_a, today=TODAY)
    assert "Brinjal" not in [c["crop"] for c in board["crops"]]
    await approve_farmer_link(result["id"], db_session, newcomer)
    board = await build_board(db_session, org_a, today=TODAY)
    assert "Brinjal" in [c["crop"] for c in board["crops"]]

    # Duplicate request is refused.
    from app.core.exceptions import ConflictError

    with pytest.raises(ConflictError):
        await create_link_request(org_a, LinkRequestIn(farmer_ref=newcomer.farmer_ref), db_session, fpo_manager)


@pytest.mark.asyncio
async def test_non_manager_fpo_staff_cannot_add_farmers(db_session):
    from app.modules.fpo_board.router import create_link_request

    platform, org_a, _, _, _ = await _setup(db_session)
    viewer = User(firebase_uid="viewer-staff", status="active")
    db_session.add(viewer)
    await db_session.flush()
    await add_staff(org_a, StaffIn(user_id=viewer.id, role="viewer"), db_session, platform)
    fpo_viewer = await _admin(db_session, AdminRole.FPO_PARTNER.value, user=viewer)
    with pytest.raises(ForbiddenError):
        await create_link_request(org_a, LinkRequestIn(farmer_ref="AGF-000000001"), db_session, fpo_viewer)


@pytest.mark.asyncio
async def test_partner_feed_farmers_never_carry_name_or_phone(db_session):
    from sqlalchemy import select

    from app.modules.admin.models import AuditLog
    from app.modules.fpo_board.router import feed_farmers

    _, org_a, _, _, raja = await _setup(db_session)
    ctx = PartnerApiKeyContext(organization_id=org_a, organization_name="FPO Alpha", key_id=uuid.uuid4())
    rows = await feed_farmers(db_session, ctx)
    assert raja.farmer_ref in [r["farmer_ref"] for r in rows]
    assert all("name" not in r and "phone" not in r for r in rows)
    audit = (await db_session.scalars(select(AuditLog).where(AuditLog.action == "partner_feed_farmers_read"))).all()
    assert len(audit) == 1 and audit[0].meta["rows"] == len(rows)
