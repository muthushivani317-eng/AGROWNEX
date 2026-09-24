"""Two-FPO, multi-role isolation checks for the organic partner surface.

Extends test_organic_partner_isolation.py (which only exercises a single
"manager" role) with the checks the 2026-09-18 staging handoff flagged as
still pending before sign-off:

  - Every partner staff role (manager, advisor, viewer) is confined to its
    own organization's farmers -- never another FPO's -- regardless of role.
  - Only the "manager" role may write (request a farmer link); advisor and
    viewer are read-only, same as the API contract in partner_router.py.
  - The read-only external API-key feed (partner_feed_router.py) is scoped
    to exactly the organization_id resolved server-side from the key --
    never from anything client-supplied -- and rejects missing, garbled,
    wrong-secret, and revoked keys.
"""
from __future__ import annotations

import uuid

import pytest

from app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from app.modules.admin.constants import AdminRole
from app.modules.admin.models import AdminUser
from app.modules.admin.service import AdminContext
from app.modules.auth.models import User
from app.modules.farms.models import Farm
from app.modules.organic_mvp.models import OrganicFpo
from app.modules.organic_mvp.partner_api_auth import get_partner_api_key_context
from app.modules.organic_mvp.partner_feed_router import farmer_summary, list_farmers
from app.modules.organic_mvp.partner_router import (
    ApiKeyIn,
    LinkRequestIn,
    OrganizationIn,
    StaffIn,
    add_staff,
    approve_farmer_link,
    create_api_key,
    create_organization,
    farmer_organic_summary,
    organization_farmers,
    request_farmer_link,
    revoke_api_key,
)


async def _platform_admin(db_session) -> AdminContext:
    user = User(firebase_uid=f"platform-{uuid.uuid4()}", status="active")
    db_session.add(user)
    await db_session.flush()
    admin = AdminUser(user_id=user.id, role=AdminRole.OWNER.value)
    db_session.add(admin)
    await db_session.flush()
    return AdminContext(admin=admin, permissions=frozenset())


async def _fpo_with_staff(db_session, platform, *, name, district, roles):
    """Register a real FPO plus a partner organization for it, with one
    active staff user per requested role. Marked is_test so it can never be
    confused with real pilot data (docs/AGROWAI_PROJECT_STATE pilot-data
    separation requirement).
    """
    fpo = OrganicFpo(name=name, district=district, is_test=True)
    db_session.add(fpo)
    await db_session.flush()
    org = await create_organization(
        OrganizationIn(name=name, kind="fpo", fpo_id=fpo.id, is_test=True),
        db_session,
        platform,
    )
    org_id = uuid.UUID(org["id"])
    staff_by_role: dict[str, User] = {}
    for role in roles:
        member = User(firebase_uid=f"{name}-{role}-{uuid.uuid4()}", status="active")
        db_session.add(member)
        await db_session.flush()
        await add_staff(org_id, StaffIn(user_id=member.id, role=role), db_session, platform)
        staff_by_role[role] = member
    return org_id, staff_by_role


async def _linked_farmer(db_session, org_id, manager, *, uid) -> User:
    """A farmer with one farm, actively (consent-approved) linked to org_id."""
    farmer = User(firebase_uid=uid, status="active")
    db_session.add(farmer)
    await db_session.flush()
    db_session.add(Farm(user_id=farmer.id, name=f"{uid} plot", crop="wheat"))
    await db_session.flush()
    request = await request_farmer_link(
        org_id, LinkRequestIn(farmer_ref=farmer.farmer_ref), db_session, manager
    )
    await approve_farmer_link(request["id"], db_session, farmer)
    return farmer


@pytest.mark.asyncio
async def test_two_fpos_every_staff_role_confined_to_own_organization(db_session):
    platform = await _platform_admin(db_session)
    org_a, staff_a = await _fpo_with_staff(
        db_session, platform, name="FPO Alpha", district="Madurai",
        roles=["manager", "advisor", "viewer"],
    )
    org_b, staff_b = await _fpo_with_staff(
        db_session, platform, name="FPO Beta", district="Salem", roles=["manager"],
    )
    farmer_a = await _linked_farmer(db_session, org_a, staff_a["manager"], uid="fpo-alpha-farmer")

    # Every role in org_a -- not just "manager" -- can read org_a's own
    # farmer list and organic summary.
    for role, member in staff_a.items():
        assert await organization_farmers(org_a, db_session, member) == [
            {"farmer_ref": farmer_a.farmer_ref}
        ], f"{role} could not read its own organization's farmers"
        summary = await farmer_organic_summary(org_a, farmer_a.farmer_ref, db_session, member)
        assert summary["farmer_ref"] == farmer_a.farmer_ref

    # No org_a role -- manager, advisor, or viewer -- can reach org_b: they
    # are not staff there, so the org itself is invisible (NotFoundError),
    # not merely returned empty.
    for _role, member in staff_a.items():
        with pytest.raises(NotFoundError):
            await organization_farmers(org_b, db_session, member)
        with pytest.raises(NotFoundError):
            await farmer_organic_summary(org_b, farmer_a.farmer_ref, db_session, member)

    # And the reverse: org_b's manager cannot reach org_a or its farmer.
    with pytest.raises(NotFoundError):
        await organization_farmers(org_a, db_session, staff_b["manager"])
    with pytest.raises(NotFoundError):
        await farmer_organic_summary(org_a, farmer_a.farmer_ref, db_session, staff_b["manager"])


@pytest.mark.asyncio
async def test_only_manager_role_may_request_a_farmer_link(db_session):
    platform = await _platform_admin(db_session)
    org_a, staff_a = await _fpo_with_staff(
        db_session, platform, name="FPO Gamma", district="Coimbatore",
        roles=["manager", "advisor", "viewer"],
    )
    farmer = User(firebase_uid="gamma-farmer", status="active")
    db_session.add(farmer)
    await db_session.flush()

    for role in ("advisor", "viewer"):
        with pytest.raises(ForbiddenError):
            await request_farmer_link(
                org_a, LinkRequestIn(farmer_ref=farmer.farmer_ref), db_session, staff_a[role]
            )

    request = await request_farmer_link(
        org_a, LinkRequestIn(farmer_ref=farmer.farmer_ref), db_session, staff_a["manager"]
    )
    assert request["status"] == "pending"


@pytest.mark.asyncio
async def test_partner_api_key_feed_is_scoped_server_side_to_its_own_fpo(db_session):
    platform = await _platform_admin(db_session)
    org_a, staff_a = await _fpo_with_staff(
        db_session, platform, name="FPO Delta", district="Erode", roles=["manager"],
    )
    org_b, staff_b = await _fpo_with_staff(
        db_session, platform, name="FPO Epsilon", district="Trichy", roles=["manager"],
    )
    farmer_a = await _linked_farmer(db_session, org_a, staff_a["manager"], uid="delta-farmer")
    farmer_b = await _linked_farmer(db_session, org_b, staff_b["manager"], uid="epsilon-farmer")

    key_a = await create_api_key(org_a, ApiKeyIn(label="Delta website"), db_session, platform)
    key_b = await create_api_key(org_b, ApiKeyIn(label="Epsilon website"), db_session, platform)

    ctx_a = await get_partner_api_key_context(db_session, key_a["api_key"])
    ctx_b = await get_partner_api_key_context(db_session, key_b["api_key"])
    assert ctx_a.organization_id == org_a
    assert ctx_b.organization_id == org_b

    feed_a = await list_farmers(db_session, ctx_a)
    assert feed_a["count"] == 1
    assert feed_a["farmers"][0]["farmer_ref"] == farmer_a.farmer_ref

    summary = await farmer_summary(farmer_a.farmer_ref, db_session, ctx_a)
    assert summary["farmer_ref"] == farmer_a.farmer_ref

    # org_a's key must never resolve org_b's farmer -- same 404 as a
    # nonexistent farmer_ref, so a caller can't even confirm the ref exists
    # under a different organization.
    with pytest.raises(NotFoundError):
        await farmer_summary(farmer_b.farmer_ref, db_session, ctx_a)

    feed_b = await list_farmers(db_session, ctx_b)
    assert feed_b["count"] == 1
    assert feed_b["farmers"][0]["farmer_ref"] == farmer_b.farmer_ref
    with pytest.raises(NotFoundError):
        await farmer_summary(farmer_a.farmer_ref, db_session, ctx_b)


@pytest.mark.asyncio
async def test_partner_api_key_missing_garbled_wrong_or_revoked_is_rejected(db_session):
    platform = await _platform_admin(db_session)
    org_a, staff_a = await _fpo_with_staff(
        db_session, platform, name="FPO Zeta", district="Dindigul", roles=["manager"],
    )
    key = await create_api_key(org_a, ApiKeyIn(label="Zeta website"), db_session, platform)
    prefix, _, _secret = key["api_key"].partition(".")

    with pytest.raises(UnauthorizedError):
        await get_partner_api_key_context(db_session, None)
    with pytest.raises(UnauthorizedError):
        await get_partner_api_key_context(db_session, "not-a-valid-key-format")
    with pytest.raises(UnauthorizedError):
        await get_partner_api_key_context(db_session, f"{prefix}.wrong-secret")

    # The real key works until it is revoked...
    ctx = await get_partner_api_key_context(db_session, key["api_key"])
    assert ctx.organization_id == org_a

    await revoke_api_key(org_a, uuid.UUID(key["id"]), db_session, platform)
    with pytest.raises(UnauthorizedError):
        await get_partner_api_key_context(db_session, key["api_key"])
