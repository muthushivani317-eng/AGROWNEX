"""Partner organizations must never inherit platform-admin or other-org access."""
import pytest
from sqlalchemy import select

from app.core.exceptions import ForbiddenError, NotFoundError
from app.modules.auth.models import User
from app.modules.admin.constants import AdminRole
from app.modules.admin.models import AdminUser
from app.modules.admin.service import AdminContext
from app.modules.farms.models import Farm
from app.modules.organic_mvp.models import OrganicPartnerOrganization, OrganicPartnerStaff
from app.modules.organic_mvp.partner_router import (
    LinkRequestIn, approve_farmer_link, farmer_organic_summary,
    organization_farmers, request_farmer_link, revoke_farmer_link,
    create_organization, deactivate_staff, OrganizationIn,
)


@pytest.mark.asyncio
async def test_two_organizations_cannot_cross_read_or_bypass_farmer_consent(db_session):
    farmer = User(firebase_uid="partner-farmer", status="active")
    manager_a = User(firebase_uid="partner-manager-a", status="active")
    manager_b = User(firebase_uid="partner-manager-b", status="active")
    db_session.add_all([farmer, manager_a, manager_b])
    await db_session.flush()
    farm = Farm(user_id=farmer.id, name="Farmer's plot")
    org_a = OrganicPartnerOrganization(name="Test KVK A", kind="kvk", is_test=True)
    org_b = OrganicPartnerOrganization(name="Test KVK B", kind="kvk", is_test=True)
    db_session.add_all([farm, org_a, org_b])
    await db_session.flush()
    db_session.add_all([
        OrganicPartnerStaff(organization_id=org_a.id, user_id=manager_a.id, role="manager", status="active"),
        OrganicPartnerStaff(organization_id=org_b.id, user_id=manager_b.id, role="manager", status="active"),
    ])
    await db_session.commit()

    request = await request_farmer_link(org_a.id, LinkRequestIn(farmer_ref=farmer.farmer_ref), db_session, manager_a)
    assert request["status"] == "pending"
    assert await organization_farmers(org_a.id, db_session, manager_a) == []
    with pytest.raises(NotFoundError):
        await farmer_organic_summary(org_a.id, farmer.farmer_ref, db_session, manager_a)

    with pytest.raises(NotFoundError):
        await organization_farmers(org_a.id, db_session, manager_b)

    await approve_farmer_link(request["id"], db_session, farmer)
    assert await organization_farmers(org_a.id, db_session, manager_a) == [{"farmer_ref": farmer.farmer_ref}]
    summary = await farmer_organic_summary(org_a.id, farmer.farmer_ref, db_session, manager_a)
    assert summary["farms"][0]["farm_name"] == "Farmer's plot"
    assert "produce" not in str(summary).lower()
    assert await organization_farmers(org_b.id, db_session, manager_b) == []
    with pytest.raises(NotFoundError):
        await farmer_organic_summary(org_b.id, farmer.farmer_ref, db_session, manager_b)
    with pytest.raises(NotFoundError):
        await revoke_farmer_link(request["id"], db_session, manager_a)

    await revoke_farmer_link(request["id"], db_session, farmer)
    assert await organization_farmers(org_a.id, db_session, manager_a) == []
    with pytest.raises(NotFoundError):
        await farmer_organic_summary(org_a.id, farmer.farmer_ref, db_session, manager_a)

    platform_user = User(firebase_uid="partner-platform-admin", status="active")
    db_session.add(platform_user)
    await db_session.flush()
    platform_admin = AdminUser(user_id=platform_user.id, role=AdminRole.OWNER.value)
    db_session.add(platform_admin)
    await db_session.flush()
    staff_a = await db_session.scalar(select(OrganicPartnerStaff).where(
        OrganicPartnerStaff.organization_id == org_a.id,
        OrganicPartnerStaff.user_id == manager_a.id,
    ))
    await deactivate_staff(org_a.id, staff_a.id, db_session,
        AdminContext(admin=platform_admin, permissions=frozenset()))
    with pytest.raises(NotFoundError):
        await organization_farmers(org_a.id, db_session, manager_a)


@pytest.mark.asyncio
async def test_partner_identity_cannot_create_organization(db_session):
    class NotPlatformAdmin:
        admin = type("Admin", (), {"role": "partner_manager"})()

    with pytest.raises(ForbiddenError):
        await create_organization(OrganizationIn(name="Unapproved KVK", kind="kvk"), db_session, NotPlatformAdmin())
