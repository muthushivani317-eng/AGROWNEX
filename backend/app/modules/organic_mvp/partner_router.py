"""Consent-based partner access to organic farmer records; never commercial data."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.modules.admin.constants import AdminRole
from app.modules.admin.dependencies import AdminContextDep
from app.modules.admin.models import AuditLog
from app.modules.auth.dependencies import CurrentUser
from app.modules.auth.models import User
from app.modules.auth.security import generate_refresh_token, hash_token
from app.modules.farms.models import Farm
from app.modules.organic_mvp.models import (
    OrganicFpo,
    OrganicPartnerApiKey,
    OrganicPartnerFarmerLink,
    OrganicPartnerOrganization,
    OrganicPartnerStaff,
    OrganicPlot,
    OrganicReadiness,
)
from app.modules.organic_mvp.schemas import FpoIn

router = APIRouter(prefix="/organic-partner", tags=["organic-partner"])
admin_router = APIRouter(prefix="/admin/organic-partner", tags=["organic-partner-admin"])
Session = Annotated[AsyncSession, Depends(get_session)]
PLATFORM_ROLES = {AdminRole.OWNER.value, AdminRole.SUPER_ADMIN.value}


class OrganizationIn(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    kind: Literal["fpo", "kvk", "agri_community"]
    fpo_id: uuid.UUID | None = None
    is_test: bool = False


class StaffIn(BaseModel):
    user_id: uuid.UUID
    role: Literal["manager", "advisor", "viewer"]


class ApiKeyIn(BaseModel):
    label: str = Field(min_length=2, max_length=120)


class LinkRequestIn(BaseModel):
    farmer_ref: str = Field(pattern=r"^AGF-[0-9]{9}$")

    @field_validator("farmer_ref", mode="before")
    @classmethod
    def _normalize_farmer_ref(cls, value: object) -> object:
        # A coordinator typing this by hand may add spaces or lowercase it;
        # the code itself is always stored/generated upper-case (see
        # app.modules.auth.models.User._sqlite_farmer_ref / the Postgres
        # sequence), so normalize before the pattern check runs.
        return value.strip().upper() if isinstance(value, str) else value


def _platform(admin) -> None:
    if admin.admin.role not in PLATFORM_ROLES:
        raise ForbiddenError("AgrowAI platform administration required.")


async def _staff(session: AsyncSession, organization_id: uuid.UUID, user_id: uuid.UUID) -> OrganicPartnerStaff:
    staff = await session.scalar(select(OrganicPartnerStaff).where(
        OrganicPartnerStaff.organization_id == organization_id,
        OrganicPartnerStaff.user_id == user_id,
        OrganicPartnerStaff.status == "active",
    ))
    if staff is None:
        raise NotFoundError("Organization not found.")
    return staff


async def _linked_farmer(session: AsyncSession, organization_id: uuid.UUID, farmer_ref: str) -> User:
    farmer = await session.scalar(select(User).join(
        OrganicPartnerFarmerLink, OrganicPartnerFarmerLink.farmer_user_id == User.id,
    ).where(
        User.farmer_ref == farmer_ref,
        User.deleted_at.is_(None),
        OrganicPartnerFarmerLink.organization_id == organization_id,
        OrganicPartnerFarmerLink.status == "active",
    ))
    if farmer is None:
        raise NotFoundError("Farmer not found in this organization.")
    return farmer


@admin_router.post("/fpos")
async def create_fpo(body: FpoIn, session: Session, admin: AdminContextDep):
    """Register an FPO so it can be turned into a partner organization below.

    Previously there was no route for this at all — `FpoIn` existed but was
    never wired up, which meant `create_organization`'s `kind == "fpo"` path
    (below) could never succeed, since it requires an existing `OrganicFpo`
    row and there was no way to create one.
    """
    _platform(admin)
    row = OrganicFpo(**body.model_dump())
    session.add(row)
    session.add(AuditLog(admin_id=admin.admin.id, role=admin.admin.role,
        action="organic_fpo_created", target="organic_fpo", target_id=str(row.id),
        ip_address=admin.ip_address,
        meta={"name": body.name, "district": body.district, "is_test": body.is_test}))
    await session.commit()
    return {"id": str(row.id), "name": row.name, "district": row.district}


@admin_router.get("/fpos")
async def list_fpos(session: Session, admin: AdminContextDep):
    _platform(admin)
    rows = (await session.scalars(
        select(OrganicFpo).order_by(OrganicFpo.name)
    )).all()
    return [
        {
            "id": str(row.id),
            "name": row.name,
            "district": row.district,
            "registration_reference": row.registration_reference,
            "is_test": row.is_test,
        }
        for row in rows
    ]


@admin_router.delete("/fpos/{fpo_id}")
async def delete_fpo(fpo_id: uuid.UUID, session: Session, admin: AdminContextDep):
    """Remove a mistaken/duplicate FPO entry.

    Previously there was no way to remove an FPO once created via POST
    /fpos -- not even a test one -- with no UI or API path and no
    `deleted_at` column on the table. Refuses to delete an FPO that
    already has a linked partner organization, since that link would be
    left dangling.
    """
    _platform(admin)
    fpo = await session.get(OrganicFpo, fpo_id)
    if fpo is None:
        raise NotFoundError("FPO not found.")
    linked = await session.scalar(select(OrganicPartnerOrganization).where(
        OrganicPartnerOrganization.fpo_id == fpo_id,
    ))
    if linked is not None:
        raise ConflictError("This FPO has a linked partner organization; remove that first.")
    session.add(AuditLog(admin_id=admin.admin.id, role=admin.admin.role,
        action="organic_fpo_deleted", target="organic_fpo", target_id=str(fpo.id),
        ip_address=admin.ip_address,
        meta={"name": fpo.name, "district": fpo.district, "is_test": fpo.is_test}))
    await session.delete(fpo)
    await session.commit()
    return {"status": "deleted"}


@admin_router.get("/organizations")
async def list_organizations(session: Session, admin: AdminContextDep):
    """All partner organizations (FPO / KVK / agri-community), for the Owner
    to find an org's ID when adding staff or checking its farmer list —
    previously there was no way to see what already exists without a direct
    database query.
    """
    _platform(admin)
    rows = (await session.scalars(
        select(OrganicPartnerOrganization).order_by(OrganicPartnerOrganization.name)
    )).all()
    return [
        {
            "id": str(row.id),
            "name": row.name,
            "kind": row.kind,
            "fpo_id": str(row.fpo_id) if row.fpo_id else None,
            "is_test": row.is_test,
        }
        for row in rows
    ]


@admin_router.get("/organizations/{organization_id}/farmers")
async def admin_organization_farmers(
    organization_id: uuid.UUID, session: Session, admin: AdminContextDep
):
    """Platform oversight of any organization's linked farmers, without the
    Owner needing to also be added as that organization's staff.
    """
    _platform(admin)
    organization = await session.get(OrganicPartnerOrganization, organization_id)
    if organization is None:
        raise NotFoundError("Organization not found.")
    rows = (await session.scalars(select(User).join(
        OrganicPartnerFarmerLink, OrganicPartnerFarmerLink.farmer_user_id == User.id,
    ).where(OrganicPartnerFarmerLink.organization_id == organization_id,
            OrganicPartnerFarmerLink.status == "active", User.deleted_at.is_(None))
        .order_by(User.farmer_ref))).all()
    return [{"farmer_ref": row.farmer_ref} for row in rows]


@admin_router.post("/organizations")
async def create_organization(body: OrganizationIn, session: Session, admin: AdminContextDep):
    _platform(admin)
    if body.kind == "fpo":
        fpo = await session.get(OrganicFpo, body.fpo_id) if body.fpo_id else None
        if fpo is None or fpo.is_test != body.is_test:
            raise ValidationError("An existing FPO in the same data environment is required.")
    elif body.fpo_id is not None:
        raise ValidationError("Only FPO organizations may reference an FPO.")
    row = OrganicPartnerOrganization(**body.model_dump())
    session.add(row)
    session.add(AuditLog(admin_id=admin.admin.id, role=admin.admin.role,
        action="organic_partner_org_created", target="organic_partner_org", target_id=str(row.id),
        ip_address=admin.ip_address,
        meta={"kind": body.kind, "fpo_id": str(body.fpo_id) if body.fpo_id else None,
              "is_test": body.is_test}))
    await session.commit()
    return {"id": str(row.id), "kind": row.kind, "is_test": row.is_test}


@admin_router.post("/organizations/{organization_id}/staff")
async def add_staff(organization_id: uuid.UUID, body: StaffIn, session: Session, admin: AdminContextDep):
    _platform(admin)
    organization = await session.get(OrganicPartnerOrganization, organization_id)
    member = await session.get(User, body.user_id)
    if organization is None or member is None or member.deleted_at is not None or member.status != "active":
        raise NotFoundError("Organization or user not found.")
    existing = await session.scalar(select(OrganicPartnerStaff).where(
        OrganicPartnerStaff.organization_id == organization_id,
        OrganicPartnerStaff.user_id == body.user_id,
    ))
    if existing:
        raise ConflictError("Staff membership already exists.")
    row = OrganicPartnerStaff(organization_id=organization_id, **body.model_dump())
    session.add(row)
    session.add(AuditLog(admin_id=admin.admin.id, role=admin.admin.role,
        action="organic_partner_staff_added", target="organic_partner_staff", target_id=str(row.id),
        ip_address=admin.ip_address,
        meta={"organization_id": str(organization_id), "user_id": str(body.user_id), "role": body.role}))
    await session.commit()
    return {"id": str(row.id), "status": row.status}


@admin_router.post("/organizations/{organization_id}/staff/{staff_id}/deactivate")
async def deactivate_staff(organization_id: uuid.UUID, staff_id: uuid.UUID, session: Session, admin: AdminContextDep):
    _platform(admin)
    staff = await session.scalar(select(OrganicPartnerStaff).where(
        OrganicPartnerStaff.id == staff_id,
        OrganicPartnerStaff.organization_id == organization_id,
        OrganicPartnerStaff.status == "active",
    ))
    if staff is None:
        raise NotFoundError("Active staff membership not found.")
    staff.status = "inactive"
    session.add(AuditLog(admin_id=admin.admin.id, role=admin.admin.role,
        action="organic_partner_staff_removed", target="organic_partner_staff", target_id=str(staff.id),
        ip_address=admin.ip_address,
        meta={"organization_id": str(organization_id), "user_id": str(staff.user_id)}))
    await session.commit()
    return {"status": staff.status}


@admin_router.post("/organizations/{organization_id}/api-keys")
async def create_api_key(organization_id: uuid.UUID, body: ApiKeyIn, session: Session, admin: AdminContextDep):
    """Issue a new API key for this organization's external website feed
    (see partner_feed_router.py). The plaintext key is returned ONCE here --
    only its prefix (for lookup) and a peppered hash are stored, the same
    pattern used for refresh tokens (app.modules.auth.security).
    """
    _platform(admin)
    organization = await session.get(OrganicPartnerOrganization, organization_id)
    if organization is None:
        raise NotFoundError("Organization not found.")
    plaintext, digest = generate_refresh_token()
    prefix = f"pak_{uuid.uuid4().hex[:10]}"
    row = OrganicPartnerApiKey(
        organization_id=organization_id, label=body.label,
        key_prefix=prefix, key_hash=hash_token(plaintext),
    )
    session.add(row)
    session.add(AuditLog(admin_id=admin.admin.id, role=admin.admin.role,
        action="organic_partner_api_key_created", target="organic_partner_api_key", target_id=str(row.id),
        ip_address=admin.ip_address,
        meta={"organization_id": str(organization_id), "label": body.label}))
    await session.commit()
    return {
        "id": str(row.id),
        "label": row.label,
        # Shown once. Format: "<prefix>.<secret>" -- the FPO's website sends
        # this whole string back as the X-Partner-Api-Key header.
        "api_key": f"{prefix}.{plaintext}",
    }


@admin_router.get("/organizations/{organization_id}/api-keys")
async def list_api_keys(organization_id: uuid.UUID, session: Session, admin: AdminContextDep):
    _platform(admin)
    rows = (await session.scalars(select(OrganicPartnerApiKey).where(
        OrganicPartnerApiKey.organization_id == organization_id,
    ).order_by(OrganicPartnerApiKey.created_at.desc()))).all()
    return [
        {
            "id": str(row.id),
            "label": row.label,
            "key_prefix": row.key_prefix,
            "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None,
            "revoked_at": row.revoked_at.isoformat() if row.revoked_at else None,
        }
        for row in rows
    ]


@admin_router.post("/organizations/{organization_id}/api-keys/{key_id}/revoke")
async def revoke_api_key(organization_id: uuid.UUID, key_id: uuid.UUID, session: Session, admin: AdminContextDep):
    _platform(admin)
    key = await session.scalar(select(OrganicPartnerApiKey).where(
        OrganicPartnerApiKey.id == key_id,
        OrganicPartnerApiKey.organization_id == organization_id,
        OrganicPartnerApiKey.revoked_at.is_(None),
    ))
    if key is None:
        raise NotFoundError("Active API key not found.")
    key.revoked_at = datetime.now(UTC)
    session.add(AuditLog(admin_id=admin.admin.id, role=admin.admin.role,
        action="organic_partner_api_key_revoked", target="organic_partner_api_key", target_id=str(key.id),
        ip_address=admin.ip_address,
        meta={"organization_id": str(organization_id)}))
    await session.commit()
    return {"status": "revoked"}


@router.post("/organizations/{organization_id}/link-requests")
async def request_farmer_link(organization_id: uuid.UUID, body: LinkRequestIn, session: Session, user: CurrentUser):
    staff = await _staff(session, organization_id, user.id)
    if staff.role != "manager":
        raise ForbiddenError("Organization manager role required.")
    farmer = await session.scalar(select(User).where(User.farmer_ref == body.farmer_ref, User.deleted_at.is_(None)))
    if farmer is None:
        raise NotFoundError("Farmer not found.")
    existing = await session.scalar(select(OrganicPartnerFarmerLink).where(
        OrganicPartnerFarmerLink.organization_id == organization_id,
        OrganicPartnerFarmerLink.farmer_user_id == farmer.id,
    ))
    if existing and existing.status != "revoked":
        raise ConflictError("Farmer link already requested or active.")
    if existing:
        existing.status = "pending"
        existing.requested_by_user_id = user.id
        existing.approved_at = None
        existing.revoked_at = None
        row = existing
    else:
        row = OrganicPartnerFarmerLink(organization_id=organization_id,
            farmer_user_id=farmer.id, requested_by_user_id=user.id, status="pending")
        session.add(row)
    session.add(AuditLog(role="organic_partner_manager", action="organic_partner_link_requested",
        target="organic_partner_farmer_link", target_id=str(row.id),
        meta={"actor_user_id": str(user.id), "organization_id": str(organization_id),
              "farmer_user_id": str(farmer.id)}))
    await session.commit()
    return {"id": str(row.id), "status": "pending"}


@router.get("/my-link-requests")
async def my_link_requests(session: Session, user: CurrentUser):
    rows = (await session.execute(select(OrganicPartnerFarmerLink, OrganicPartnerOrganization)
        .join(OrganicPartnerOrganization, OrganicPartnerOrganization.id == OrganicPartnerFarmerLink.organization_id)
        .where(OrganicPartnerFarmerLink.farmer_user_id == user.id)
        .order_by(OrganicPartnerFarmerLink.created_at.desc()))).all()
    return [{"id": str(link.id), "organization_name": organization.name,
             "organization_kind": organization.kind, "status": link.status}
            for link, organization in rows]


@router.post("/my-link-requests/{link_id}/approve")
async def approve_farmer_link(link_id: uuid.UUID, session: Session, user: CurrentUser):
    link = await session.scalar(select(OrganicPartnerFarmerLink).where(
        OrganicPartnerFarmerLink.id == link_id,
        OrganicPartnerFarmerLink.farmer_user_id == user.id,
        OrganicPartnerFarmerLink.status == "pending",
    ))
    if link is None:
        raise NotFoundError("Pending link request not found.")
    link.status = "active"
    link.approved_at = datetime.now(UTC)
    session.add(AuditLog(role="farmer", action="organic_partner_link_approved",
        target="organic_partner_farmer_link", target_id=str(link.id),
        meta={"actor_user_id": str(user.id), "organization_id": str(link.organization_id)}))
    await session.commit()
    return {"status": link.status}


@router.post("/my-link-requests/{link_id}/revoke")
async def revoke_farmer_link(link_id: uuid.UUID, session: Session, user: CurrentUser):
    link = await session.scalar(select(OrganicPartnerFarmerLink).where(
        OrganicPartnerFarmerLink.id == link_id,
        OrganicPartnerFarmerLink.farmer_user_id == user.id,
        OrganicPartnerFarmerLink.status.in_(["pending", "active"]),
    ))
    if link is None:
        raise NotFoundError("Link request not found.")
    link.status = "revoked"
    link.revoked_at = datetime.now(UTC)
    session.add(AuditLog(role="farmer", action="organic_partner_link_revoked",
        target="organic_partner_farmer_link", target_id=str(link.id),
        meta={"actor_user_id": str(user.id), "organization_id": str(link.organization_id)}))
    await session.commit()
    return {"status": link.status}


@router.get("/organizations/{organization_id}/farmers")
async def organization_farmers(organization_id: uuid.UUID, session: Session, user: CurrentUser):
    await _staff(session, organization_id, user.id)
    rows = (await session.scalars(select(User).join(
        OrganicPartnerFarmerLink, OrganicPartnerFarmerLink.farmer_user_id == User.id,
    ).where(OrganicPartnerFarmerLink.organization_id == organization_id,
            OrganicPartnerFarmerLink.status == "active", User.deleted_at.is_(None))
        .order_by(User.farmer_ref).limit(100))).all()
    return [{"farmer_ref": row.farmer_ref} for row in rows]


@router.get("/organizations/{organization_id}/farmers/{farmer_ref}/organic-summary")
async def farmer_organic_summary(organization_id: uuid.UUID, farmer_ref: str, session: Session, user: CurrentUser):
    await _staff(session, organization_id, user.id)
    farmer = await _linked_farmer(session, organization_id, farmer_ref)
    farms = (await session.scalars(select(Farm).where(Farm.user_id == farmer.id, Farm.deleted_at.is_(None)))).all()
    summaries = []
    for farm in farms:
        plots = (await session.scalars(select(OrganicPlot).where(OrganicPlot.farm_id == farm.id))).all()
        readiness = await session.scalar(select(OrganicReadiness).where(
            OrganicReadiness.farm_id == farm.id).order_by(OrganicReadiness.created_at.desc()))
        summaries.append({"farm_id": str(farm.id), "farm_name": farm.name,
                          "organic_plot_count": len(plots),
                          "readiness_pathway": readiness.pathway if readiness else None})
    return {"farmer_ref": farmer.farmer_ref, "farms": summaries}
