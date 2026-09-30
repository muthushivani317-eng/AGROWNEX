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
