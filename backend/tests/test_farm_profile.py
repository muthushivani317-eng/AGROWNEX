"""Onboarding v2: farm items, profile extras, FPO/KVK join and the board."""
from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.modules.admin.constants import AdminRole, permissions_for
from app.modules.admin.models import AdminUser
from app.modules.admin.service import AdminContext
from app.modules.auth.models import User
from app.modules.auth.schemas import ProfileUpdateRequest
from app.modules.auth.service import AuthService
from app.modules.farm_profile.router import (
    farm_catalog,
    join_organization,
    my_farm_items,
    partner_directory,
    replace_farm_items,
)
from app.modules.farm_profile.schemas import FarmItemIn, FarmItemsIn, JoinRequestIn
from app.modules.fpo_board.router import (
    OrganizationSettingsIn,
    accept_join_request,
    list_link_requests,
    list_organizations,
    organization_farmer_csv,
    organization_farmer_list,
    reject_join_request,
    update_organization_settings,
)
from app.modules.fpo_board.service import build_board
from app.modules.organic_mvp.models import OrganicFpo
from app.modules.organic_mvp.partner_router import (
    LinkRequestIn,
    OrganizationIn,
    StaffIn,
    add_staff,
    create_organization,
    my_link_requests,
    request_farmer_link,
    revoke_farmer_link,
)


def _data(response):
    data = response.data
    if isinstance(data, list):
        return [d.model_dump() if hasattr(d, "model_dump") else d for d in data]
    return data


async def _admin(db_session, role: str, user: User | None = None) -> AdminContext:
    if user is None:
        user = User(firebase_uid=f"admin-{uuid.uuid4()}", status="active")
        db_session.add(user)
        await db_session.flush()
    admin = AdminUser(user_id=user.id, role=role)
    db_session.add(admin)
    await db_session.flush()
    return AdminContext(admin=admin, permissions=frozenset(permissions_for(role)))


async def _user(db_session, uid: str, phone: str | None = None) -> User:
    user = User(firebase_uid=uid, status="active", phone_number=phone)
    db_session.add(user)
    await db_session.flush()
    return user


async def _org(db_session, platform, name: str, kind: str = "fpo", *, listed: bool = True, district="Thoothukudi"):
    fpo_id = None
    if kind == "fpo":
        fpo = OrganicFpo(name=name, district=district, is_test=True)
        db_session.add(fpo)
        await db_session.flush()
        fpo_id = fpo.id
    org = await create_organization(OrganizationIn(name=name, kind=kind, fpo_id=fpo_id, is_test=True), db_session, platform)
    org_id = uuid.UUID(org["id"])
    manager = await _user(db_session, f"{name}-manager")
    await add_staff(org_id, StaffIn(user_id=manager.id, role="manager"), db_session, platform)
    await update_organization_settings(
        org_id, OrganizationSettingsIn(district=district, listed_in_app=listed), db_session, platform
    )
    return org_id, manager


async def _onboard(db_session, user: User, *, name: str, village: str, needs: list[str], items: list[FarmItemIn]):
    await AuthService(db_session).upsert_profile(
        user,
        ProfileUpdateRequest(
            full_name=name,
            district="Thoothukudi",
            block="Srivaikuntam",
            village=village,
            experience_years=10,
            land_holding_acres=3.5,
            farmer_type="full_time_farmer",
            landmark="Near temple",
            needs=needs,
        ),
    )
    await db_session.commit()
    await replace_farm_items(FarmItemsIn(items=items), db_session, user)


def test_catalog_and_item_validation():
    with pytest.raises(ValidationError):
        FarmItemIn(item_code="not_a_crop")
    with pytest.raises(ValidationError):
        FarmItemIn(item_code="other", category="crops")  # custom_name missing
    with pytest.raises(ValidationError):
        FarmItemIn(item_code="tomato", harvest_months=[13])
    with pytest.raises(ValidationError):
        FarmItemsIn(items=[FarmItemIn(item_code="tomato"), FarmItemIn(item_code="tomato")])
    with pytest.raises(ValidationError):
        ProfileUpdateRequest(full_name="Raja", needs=["unicorns"])
    with pytest.raises(ValidationError):
        JoinRequestIn(consent=False)
    tomato = FarmItemIn(item_code="tomato", category="fruits", approx_quantity=500)
    assert tomato.category == "vegetables" and tomato.unit == "kg"  # catalog wins
    other = FarmItemIn(item_code="other", category="other_products", custom_name="  Dried   chilli ")
    assert other.custom_name == "Dried chilli"


@pytest.mark.asyncio
async def test_catalog_endpoint(db_session):
    user = await _user(db_session, "catalog-user")
    payload = _data(await farm_catalog(user))
    codes = {i["code"] for i in payload["items"]}
    assert {"paddy", "tomato", "banana", "coconut", "cow", "milk"} <= codes
    assert {c["code"] for c in payload["categories"]} == {
        "crops", "vegetables", "fruits", "plantation", "livestock", "other_products"
    }
    assert all(i["ta"] for i in payload["items"])


@pytest.mark.asyncio
async def test_profile_extras_saved_and_not_wiped_by_old_clients(db_session):
    user = await _user(db_session, "profile-user")
    service = AuthService(db_session)
    await service.upsert_profile(
        user, ProfileUpdateRequest(full_name="Raja", land_holding_acres=2.5, farmer_type="tenant_farmer", needs=["credit"])
    )
    await db_session.commit()
    # An older app build sends only the old fields.
    profile = await service.upsert_profile(user, ProfileUpdateRequest(full_name="Raja K"))
    await db_session.commit()
    assert profile.full_name == "Raja K"
    assert profile.land_holding_acres == 2.5 and profile.farmer_type == "tenant_farmer" and profile.needs == ["credit"]


@pytest.mark.asyncio
async def test_farm_items_replace_and_list(db_session):
    user = await _user(db_session, "items-user")
    await db_session.commit()
    await replace_farm_items(
        FarmItemsIn(items=[FarmItemIn(item_code="paddy", harvest_months=[1, 2]), FarmItemIn(item_code="cow", approx_quantity=3)]),
        db_session,
        user,
    )
    saved = _data(
        await replace_farm_items(FarmItemsIn(items=[FarmItemIn(item_code="banana", available_for_sale=True)]), db_session, user)
    )
    assert [i["item_code"] for i in saved] == ["banana"]
    listed = _data(await my_farm_items(db_session, user))
    assert listed[0]["name"] == "Banana" and listed[0]["name_ta"] == "வாழை" and listed[0]["unit"] == "tonne"


@pytest.mark.asyncio
async def test_join_flow_directory_accept_board(db_session):
    platform = await _admin(db_session, AdminRole.OWNER.value)
    fpo, manager = await _org(db_session, platform, "Kovil FPO")
    kvk, _ = await _org(db_session, platform, "Local KVK", kind="kvk")
    await _org(db_session, platform, "Hidden FPO", listed=False)
    far, _ = await _org(db_session, platform, "Far FPO", district="Madurai")

    farmer = await _user(db_session, "joiner", phone="+919111111111")
    await _onboard(
        db_session,
        farmer,
        name="Selvi",
        village="Kovil",
        needs=["quality_seeds", "buyers"],
        items=[
            FarmItemIn(item_code="tomato", harvest_months=[3, 4], approx_quantity=800, area_acres=1.0, available_for_sale=True),
            FarmItemIn(item_code="cow", approx_quantity=2),
            FarmItemIn(item_code="milk", approx_quantity=10, unit="litre", available_for_sale=True),
        ],
    )

    directory = _data(await partner_directory(db_session, farmer, kind="fpo", district="thoothukudi"))
    assert [d["name"] for d in directory] == ["Kovil FPO", "Far FPO"]  # hidden excluded, same district first
    assert [d["name"] for d in _data(await partner_directory(db_session, farmer, kind="kvk", district=None))] == ["Local KVK"]

    joined = _data(await join_organization(fpo, JoinRequestIn(consent=True), db_session, farmer))
    assert joined["status"] == "join_requested"
    with pytest.raises(ConflictError):
        await join_organization(fpo, JoinRequestIn(consent=True), db_session, farmer)
    mine = await my_link_requests(db_session, farmer)
    assert mine[0]["initiated_by"] == "farmer" and mine[0]["status"] == "join_requested"

    # Not on the board until the manager accepts.
    assert (await build_board(db_session, fpo))["summary"]["farmer_count"] == 0

    fpo_manager = await _admin(db_session, AdminRole.FPO_PARTNER.value, user=manager)
    [org_row] = await list_organizations(db_session, fpo_manager)
    assert org_row["join_request_count"] == 1 and org_row["listed_in_app"] is True
    [request] = await list_link_requests(fpo, db_session, fpo_manager)
    assert request["farmer"]["name"] == "Selvi" and request["farmer"]["items"] == ["Cow", "Milk", "Tomato"]

    with pytest.raises(ForbiddenError):
        await update_organization_settings(fpo, OrganizationSettingsIn(listed_in_app=False), db_session, fpo_manager)

    await accept_join_request(fpo, uuid.UUID(request["id"]), db_session, fpo_manager)
    board = await build_board(db_session, fpo)
    assert board["summary"]["farmer_count"] == 1
    assert board["summary"]["total_land_holding_acres"] == 3.5
    assert [c["crop"] for c in board["crops"]] == ["Tomato"]  # livestock/products are not crops
    items = {i["code"]: i for i in board["farm_items"]}
    assert items["tomato"]["approx_quantity"] == {"kg": 800.0}
    assert items["tomato"]["for_sale_quantity"] == {"kg": 800.0}
    assert items["tomato"]["harvest_months"] == [3, 4]
    assert items["cow"]["for_sale_farmer_count"] == 0
    march = next(m for m in board["harvest_calendar"] if m["month"] == 3)
    assert march["items"] == [{"code": "tomato", "name": "Tomato", "farmer_count": 1}]
    assert {n["code"] for n in board["needs"]} == {"quality_seeds", "buyers"}

    rows = await organization_farmer_list(fpo, db_session, fpo_manager, need="buyers")
    assert rows[0]["land_holding_acres"] == 3.5 and len(rows[0]["farm_items"]) == 3
    assert await organization_farmer_list(fpo, db_session, fpo_manager, need="credit") == []
    assert len(await organization_farmer_list(fpo, db_session, fpo_manager, harvest_month=4)) == 1
    assert len(await organization_farmer_list(fpo, db_session, fpo_manager, crop="tomato")) == 1
    csv_text = (await organization_farmer_csv(fpo, db_session, fpo_manager)).body.decode()
    assert "land_acres" in csv_text.splitlines()[0] and "Tomato 800 kg harvest Mar/Apr [for sale]" in csv_text

    # Farmer can leave; other org's manager sees nothing.
    await revoke_farmer_link(uuid.UUID(request["id"]), db_session, farmer)
    assert (await build_board(db_session, fpo))["summary"]["farmer_count"] == 0
    assert (await build_board(db_session, far))["summary"]["farmer_count"] == 0


@pytest.mark.asyncio
async def test_join_edge_cases(db_session):
    platform = await _admin(db_session, AdminRole.OWNER.value)
    fpo, manager = await _org(db_session, platform, "Edge FPO")
    hidden, _ = await _org(db_session, platform, "Hidden", listed=False)
    farmer = await _user(db_session, "edge-farmer")
    await db_session.commit()

    with pytest.raises(NotFoundError):
        await join_organization(hidden, JoinRequestIn(consent=True), db_session, farmer)

    # FPO asked first -> farmer tapping Join approves it directly.
    await request_farmer_link(fpo, LinkRequestIn(farmer_ref=farmer.farmer_ref), db_session, manager)
    assert _data(await join_organization(fpo, JoinRequestIn(consent=True), db_session, farmer))["status"] == "active"
    with pytest.raises(ConflictError):
        await join_organization(fpo, JoinRequestIn(consent=True), db_session, farmer)

    # Rejection, and viewer staff cannot accept.
    other = await _user(db_session, "edge-other")
    await db_session.commit()
    link = _data(await join_organization(fpo, JoinRequestIn(consent=True), db_session, other))
    viewer = await _user(db_session, "edge-viewer")
    await add_staff(fpo, StaffIn(user_id=viewer.id, role="viewer"), db_session, platform)
    viewer_admin = await _admin(db_session, AdminRole.FPO_PARTNER.value, user=viewer)
    with pytest.raises(ForbiddenError):
        await accept_join_request(fpo, uuid.UUID(link["id"]), db_session, viewer_admin)
    await reject_join_request(fpo, uuid.UUID(link["id"]), db_session, platform)
    with pytest.raises(NotFoundError):
        await accept_join_request(fpo, uuid.UUID(link["id"]), db_session, platform)
    # Rejected farmer may ask again later.
    assert _data(await join_organization(fpo, JoinRequestIn(consent=True), db_session, other))["status"] == "join_requested"


# --- App onboarding payload (PUT /farmers/me from CompleteProfileScreen) ---
APP_PAYLOAD = {
    "full_name": "Muthu",
    "language": "ta",
    "district": "Thoothukudi",
    "block": "Srivaikuntam",
    "village": "Kovil",
    "experience_years": 12,
    "preferred_crops": ["paddy"],
    "land_holding_acres": 4.5,
    "farmer_type": "small",
    "landmark": "Near school",
    "latitude": 8.63,
    "longitude": 77.91,
    "farm_products": [
        {"product_id": "paddy", "category": "crops", "expected_harvest_month": "2027-01",
         "approximate_quantity": 40, "unit": "quintal", "available_for_sale": True},
        {"product_id": "redgram", "category": "crops", "expected_harvest_month": None,
         "approximate_quantity": None, "unit": "kg", "available_for_sale": False},
        {"product_id": "goat", "category": "livestock", "approximate_quantity": 6, "unit": "count"},
        {"product_id": "cow_milk", "category": "livestock", "approximate_quantity": 20, "unit": "litre",
         "available_for_sale": True},
        {"product_id": "compost", "category": "other", "approximate_quantity": 2, "unit": "tonne"},
        {"product_id": "dragon_fruit", "category": "fruits", "approximate_quantity": 50, "unit": "kg"},
    ],
    "wants_fpo_support": True,
    "wants_kvk_support": False,
}


@pytest.mark.asyncio
async def test_app_onboarding_payload_lands_in_farm_items_and_board(db_session):
    from datetime import date

    from app.modules.farm_profile.service import app_products_out, list_items
    from app.modules.farmers.schemas import FarmerMeUpdate
    from app.modules.farmers.service import FarmerService

    farmer = await _user(db_session, "app-farmer", phone="+919222222222")
    await db_session.commit()
    profile = await FarmerService(db_session).update_me(farmer, FarmerMeUpdate(**APP_PAYLOAD))
    await db_session.commit()

    assert profile.farmer_type == "small_farmer" and profile.land_holding_acres == 4.5
    assert profile.latitude == 8.63 and profile.wants_fpo_support is True and profile.wants_kvk_support is False
    rows = {r.item_code if r.item_code != "other" else r.custom_name: r for r in await list_items(db_session, farmer.id)}
    assert set(rows) == {"paddy", "red_gram", "goat", "milk", "compost", "dragon fruit"}
    assert rows["paddy"].harvest_months == [1] and rows["paddy"].available_for_sale is True
    assert rows["goat"].unit == "head" and rows["goat"].approx_quantity == 6
    assert rows["milk"].category == "other_products" and rows["dragon fruit"].category == "fruits"

    # Round-trips back in the app's shape.
    out = {p.product_id: p for p in app_products_out(list(rows.values()), today=date(2026, 9, 30))}
    assert out["redgram"].unit == "kg" and out["cow_milk"].available_for_sale is True
    assert out["paddy"].expected_harvest_month == "2027-01" and out["goat"].unit == "count"

    # Old app build without farm_products / flags keeps them.
    await FarmerService(db_session).update_me(farmer, FarmerMeUpdate(full_name="Muthu K", wants_fpo_support=None))
    await db_session.commit()
    assert len(await list_items(db_session, farmer.id)) == 6
    assert profile.wants_fpo_support is True

    # FPO sees it once linked.
    platform = await _admin(db_session, AdminRole.OWNER.value)
    fpo, manager = await _org(db_session, platform, "App FPO")
    await join_organization(fpo, JoinRequestIn(consent=True), db_session, farmer)
    [request] = await list_link_requests(fpo, db_session, platform)
    await accept_join_request(fpo, uuid.UUID(request["id"]), db_session, platform)
    board = await build_board(db_session, fpo)
    assert {i["code"] for i in board["farm_items"]} >= {"paddy", "goat", "milk"}
    assert board["summary"]["farmer_types"][0]["code"] == "small_farmer"


@pytest.mark.asyncio
async def test_all_farmers_view_before_any_fpo_and_farmer_detail(db_session):
    from app.modules.admin.queries import AdminQueries
    from app.modules.admin.schemas import FarmerDetailOut
    from app.modules.farmers.schemas import FarmerMeUpdate
    from app.modules.farmers.service import FarmerService
    from app.modules.fpo_board.router import all_farmers_board, all_farmers_csv, all_farmers_list

    farmer = await _user(db_session, "no-fpo-farmer", phone="+919333333333")
    await db_session.commit()
    await FarmerService(db_session).update_me(farmer, FarmerMeUpdate(**APP_PAYLOAD))
    await db_session.commit()
    platform = await _admin(db_session, AdminRole.OWNER.value)
    await db_session.commit()

    board = await all_farmers_board(db_session, platform)
    assert board["organization"]["id"] == "all"
    assert board["summary"]["farmer_count"] >= 1 and board["summary"]["wants_fpo_support"] == 1
    assert "paddy" in {i["code"] for i in board["farm_items"]}
    rows = await all_farmers_list(db_session, platform, support="fpo")
    assert [r["farmer_ref"] for r in rows] == [farmer.farmer_ref]
    assert await all_farmers_list(db_session, platform, support="kvk") == []
    csv_text = (await all_farmers_csv(db_session, platform)).body.decode()
    assert "wants_support" in csv_text.splitlines()[0] and "FPO" in csv_text

    fpo_partner = await _admin(db_session, AdminRole.FPO_PARTNER.value)
    with pytest.raises(ForbiddenError):
        await all_farmers_board(db_session, fpo_partner)

    detail = await AdminQueries(db_session).farmer_detail(farmer.id)
    detail["consents"] = []
    out = FarmerDetailOut.from_detail(farmer.id, detail)
    assert out.land_holding_acres == 4.5 and out.farmer_type == "Small farmer"
    assert out.wants_fpo_support is True and out.latitude == 8.63
    assert {i["name"] for i in out.farm_items} >= {"Paddy", "Goat", "Milk"}
