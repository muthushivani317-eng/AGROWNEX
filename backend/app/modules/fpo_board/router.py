"""FPO Crop Board endpoints.

- Admin Web (`/admin/fpo-board`): platform admins (Owner/Super Admin) see any
  organization; an `fpo_partner` admin sees only organizations where their own
  user is ACTIVE partner staff (organic_mvp.OrganicPartnerStaff). The
  organization id in the URL is always re-checked server-side.
- Partner feed (`/partner-feed/crop-board`): organization resolved from the
  API key only, never from the request.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.modules.admin.constants import AdminPermission, AdminRole
from app.modules.admin.dependencies import AdminContextDep
from app.modules.admin.models import AuditLog
from app.modules.auth.models import User
from app.modules.auth.profile_models import FarmerProfile
from app.modules.farm_profile.catalog import item_label
from app.modules.farm_profile.models import FarmerFarmItem
from app.modules.farm_profile.service import JOIN_REQUESTED
from app.modules.fpo_board.service import build_board, farmer_rows, rows_to_csv
from app.modules.organic_mvp.models import (
    OrganicPartnerFarmerLink,
    OrganicPartnerOrganization,
    OrganicPartnerStaff,
)
from app.modules.organic_mvp.partner_api_auth import PartnerApiKeyDep, record_partner_read
from app.modules.organic_mvp.partner_router import LinkRequestIn

admin_router = APIRouter(prefix="/admin/fpo-board", tags=["fpo-board"])
feed_router = APIRouter(prefix="/partner-feed/crop-board", tags=["partner-feed"])
FEED_REDACTED_FIELDS = frozenset({"name", "phone"})
Session = Annotated[AsyncSession, Depends(get_session)]
PLATFORM_ROLES = {AdminRole.OWNER.value, AdminRole.SUPER_ADMIN.value}


class OrganizationSettingsIn(BaseModel):
    district: str | None = Field(default=None, max_length=80)
    listed_in_app: bool | None = None


def _require_permission(admin) -> None:
    if AdminPermission.VIEW_FPO_BOARD.value not in admin.permissions:
        raise ForbiddenError("You do not have permission to view the FPO crop board.")


async def _visible_org_ids(session: AsyncSession, admin) -> set[uuid.UUID] | None:
    """None = every organization (platform admin); otherwise the staff scope."""
    if admin.admin.role in PLATFORM_ROLES:
        return None
    rows = await session.scalars(
        select(OrganicPartnerStaff.organization_id).where(
            OrganicPartnerStaff.user_id == admin.admin.user_id,
            OrganicPartnerStaff.status == "active",
        )
    )
    return set(rows.all())


async def _org_for_admin(session: AsyncSession, admin, organization_id: uuid.UUID) -> OrganicPartnerOrganization:
    _require_permission(admin)
    visible = await _visible_org_ids(session, admin)
    organization = await session.get(OrganicPartnerOrganization, organization_id)
    if organization is None or (visible is not None and organization_id not in visible):
        raise NotFoundError("Organization not found.")
    return organization


def _audit(session: AsyncSession, admin, action: str, organization_id: uuid.UUID, meta: dict | None = None) -> None:
    session.add(
        AuditLog(
            admin_id=admin.admin.id,
            role=admin.admin.role,
            action=action,
            target="organic_partner_org",
            target_id=str(organization_id),
            ip_address=admin.ip_address,
            meta=meta or {},
        )
    )


@admin_router.get("/organizations")
async def list_organizations(session: Session, admin: AdminContextDep):
    _require_permission(admin)
    visible = await _visible_org_ids(session, admin)
    stmt = select(OrganicPartnerOrganization).order_by(OrganicPartnerOrganization.name)
    if visible is not None:
        if not visible:
            return []
        stmt = stmt.where(OrganicPartnerOrganization.id.in_(visible))
    organizations = (await session.scalars(stmt)).all()
    counts: dict[tuple[uuid.UUID, str], int] = {
        (org_id, status): n
        for org_id, status, n in (
            await session.execute(
                select(OrganicPartnerFarmerLink.organization_id, OrganicPartnerFarmerLink.status, func.count())
                .where(OrganicPartnerFarmerLink.status.in_(["active", JOIN_REQUESTED]))
                .group_by(OrganicPartnerFarmerLink.organization_id, OrganicPartnerFarmerLink.status)
            )
        ).all()
    }
    return [
        {
            "id": str(o.id),
            "name": o.name,
            "kind": o.kind,
            "district": o.district,
            "listed_in_app": o.listed_in_app,
            "farmer_count": counts.get((o.id, "active"), 0),
            "join_request_count": counts.get((o.id, JOIN_REQUESTED), 0),
        }
        for o in organizations
    ]


def _require_platform(admin) -> None:
    _require_permission(admin)
    if admin.admin.role not in PLATFORM_ROLES:
        raise ForbiddenError("Only the Owner or a Super Admin can view all farmers.")


def _all_audit(session: AsyncSession, admin, action: str, meta: dict) -> None:
    session.add(
        AuditLog(
            admin_id=admin.admin.id,
            role=admin.admin.role,
            action=action,
            target="farmer_network",
            target_id="all",
            ip_address=admin.ip_address,
            meta=meta,
        )
    )


@admin_router.get("/all")
async def all_farmers_board(session: Session, admin: AdminContextDep):
    """Same board across every Agrownex farmer (before any FPO/KVK exists)."""
    _require_platform(admin)
    board = await build_board(session, None)
    return {"organization": {"id": "all", "name": "All Agrownex farmers", "kind": "all", "district": None, "listed_in_app": False}, **board}


@admin_router.get("/all/farmers")
async def all_farmers_list(
    session: Session,
    admin: AdminContextDep,
    crop: Annotated[str | None, Query(max_length=80)] = None,
    product: Annotated[str | None, Query(max_length=160)] = None,
    need: Annotated[str | None, Query(max_length=40)] = None,
    harvest_month: Annotated[int | None, Query(ge=1, le=12)] = None,
    support: Annotated[Literal["fpo", "kvk"] | None, Query()] = None,
):
    _require_platform(admin)
    filters = {"crop": crop, "product": product, "need": need, "harvest_month": harvest_month, "support": support}
    rows = await farmer_rows(session, None, **filters)
    _all_audit(session, admin, "farmer_network_viewed", {**filters, "rows": len(rows)})
    await session.commit()
    return rows


@admin_router.get("/all/farmers.csv")
async def all_farmers_csv(
    session: Session,
    admin: AdminContextDep,
    crop: Annotated[str | None, Query(max_length=80)] = None,
    product: Annotated[str | None, Query(max_length=160)] = None,
    need: Annotated[str | None, Query(max_length=40)] = None,
    harvest_month: Annotated[int | None, Query(ge=1, le=12)] = None,
    support: Annotated[Literal["fpo", "kvk"] | None, Query()] = None,
):
    _require_platform(admin)
    filters = {"crop": crop, "product": product, "need": need, "harvest_month": harvest_month, "support": support}
    rows = await farmer_rows(session, None, **filters)
    _all_audit(session, admin, "farmer_network_exported", {**filters, "rows": len(rows)})
    await session.commit()
    return Response(
        content=rows_to_csv(rows),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="agrownex-farmers.csv"', "Cache-Control": "no-store"},
    )


@admin_router.patch("/organizations/{organization_id}")
async def update_organization_settings(
    organization_id: uuid.UUID, body: OrganizationSettingsIn, session: Session, admin: AdminContextDep
):
    """Platform admins set the district and whether farmers can find it in the app."""
    if admin.admin.role not in PLATFORM_ROLES:
        raise ForbiddenError("Only the Owner or a Super Admin can change this.")
    organization = await session.get(OrganicPartnerOrganization, organization_id)
    if organization is None:
        raise NotFoundError("Organization not found.")
    changes = body.model_dump(exclude_unset=True)
    if "district" in changes:
        organization.district = (changes["district"] or "").strip() or None
    if changes.get("listed_in_app") is not None:
        organization.listed_in_app = changes["listed_in_app"]
    _audit(session, admin, "fpo_board_org_settings_updated", organization_id, changes)
    await session.commit()
    return {
        "id": str(organization.id),
        "district": organization.district,
        "listed_in_app": organization.listed_in_app,
    }


@admin_router.get("/organizations/{organization_id}")
async def organization_board(organization_id: uuid.UUID, session: Session, admin: AdminContextDep):
    organization = await _org_for_admin(session, admin, organization_id)
    board = await build_board(session, organization_id)
    return {
        "organization": {
            "id": str(organization.id),
            "name": organization.name,
            "kind": organization.kind,
            "district": organization.district,
            "listed_in_app": organization.listed_in_app,
        },
        **board,
    }


@admin_router.get("/organizations/{organization_id}/farmers")
async def organization_farmer_list(
    organization_id: uuid.UUID,
    session: Session,
    admin: AdminContextDep,
    crop: Annotated[str | None, Query(max_length=80)] = None,
    product: Annotated[str | None, Query(max_length=160)] = None,
    need: Annotated[str | None, Query(max_length=40)] = None,
    harvest_month: Annotated[int | None, Query(ge=1, le=12)] = None,
):
    await _org_for_admin(session, admin, organization_id)
    filters = {"crop": crop, "product": product, "need": need, "harvest_month": harvest_month}
    rows = await farmer_rows(session, organization_id, **filters)
    _audit(session, admin, "fpo_board_farmers_viewed", organization_id, {**filters, "rows": len(rows)})
    await session.commit()
    return rows


@admin_router.get("/organizations/{organization_id}/farmers.csv")
async def organization_farmer_csv(
    organization_id: uuid.UUID,
    session: Session,
    admin: AdminContextDep,
    crop: Annotated[str | None, Query(max_length=80)] = None,
    product: Annotated[str | None, Query(max_length=160)] = None,
    need: Annotated[str | None, Query(max_length=40)] = None,
    harvest_month: Annotated[int | None, Query(ge=1, le=12)] = None,
):
    organization = await _org_for_admin(session, admin, organization_id)
    filters = {"crop": crop, "product": product, "need": need, "harvest_month": harvest_month}
    rows = await farmer_rows(session, organization_id, **filters)
    _audit(session, admin, "fpo_board_farmers_exported", organization_id, {**filters, "rows": len(rows)})
    await session.commit()
    safe_name = "".join(ch if ch.isalnum() else "-" for ch in organization.name).strip("-").lower() or "fpo"
    return Response(
        content=rows_to_csv(rows),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}-farmers.csv"', "Cache-Control": "no-store"},
    )


async def _require_manager(session: AsyncSession, admin, organization_id: uuid.UUID) -> None:
    """Adding farmers is a write: platform admins, or this FPO's manager staff."""
    if admin.admin.role in PLATFORM_ROLES:
        return
    staff = await session.scalar(
        select(OrganicPartnerStaff).where(
            OrganicPartnerStaff.organization_id == organization_id,
            OrganicPartnerStaff.user_id == admin.admin.user_id,
            OrganicPartnerStaff.status == "active",
        )
    )
    if staff is None or staff.role != "manager":
        raise ForbiddenError("Only the organization manager can add or approve farmers.")


@admin_router.get("/organizations/{organization_id}/link-requests")
async def list_link_requests(organization_id: uuid.UUID, session: Session, admin: AdminContextDep):
    """Farmer links for this organization.

    Organization-initiated requests show only the Farmer ID until the farmer
    approves. A farmer's own join request (status ``join_requested``) was sent
    with their consent, so name, village and declared items are shown to let
    the manager decide.
    """
    await _org_for_admin(session, admin, organization_id)
    rows = (
        await session.execute(
            select(OrganicPartnerFarmerLink, User)
            .join(User, User.id == OrganicPartnerFarmerLink.farmer_user_id)
            .where(OrganicPartnerFarmerLink.organization_id == organization_id, User.deleted_at.is_(None))
            .order_by(OrganicPartnerFarmerLink.updated_at.desc())
            .limit(500)
        )
    ).all()
    joiners = [user.id for link, user in rows if link.status == JOIN_REQUESTED]
    profiles, items = {}, {}
    if joiners:
        profiles = {
            p.user_id: p
            for p in (await session.scalars(select(FarmerProfile).where(FarmerProfile.user_id.in_(joiners)))).all()
        }
        for item in (await session.scalars(select(FarmerFarmItem).where(FarmerFarmItem.user_id.in_(joiners)))).all():
            items.setdefault(item.user_id, []).append(item_label(item.item_code, item.custom_name))
    result = []
    for link, user in rows:
        row = {
            "id": str(link.id),
            "farmer_ref": user.farmer_ref,
            "status": link.status,
            "initiated_by": "farmer" if link.requested_by_user_id == user.id else "organization",
            "requested_at": link.updated_at if link.status == JOIN_REQUESTED else link.created_at,
            "approved_at": link.approved_at,
            "revoked_at": link.revoked_at,
        }
        if link.status == JOIN_REQUESTED:
            profile = profiles.get(user.id)
            row["farmer"] = {
                "name": profile.full_name if profile else None,
                "phone": user.phone_number,
                "village": profile.village if profile else None,
                "block": profile.block if profile else None,
                "district": profile.district if profile else None,
                "land_holding_acres": profile.land_holding_acres if profile else None,
                "items": sorted(items.get(user.id, [])),
            }
        result.append(row)
    return result


async def _join_request(session: AsyncSession, organization_id: uuid.UUID, link_id: uuid.UUID) -> OrganicPartnerFarmerLink:
    link = await session.scalar(
        select(OrganicPartnerFarmerLink).where(
            OrganicPartnerFarmerLink.id == link_id,
            OrganicPartnerFarmerLink.organization_id == organization_id,
            OrganicPartnerFarmerLink.status == JOIN_REQUESTED,
        )
    )
    if link is None:
        raise NotFoundError("Join request not found.")
    return link


@admin_router.post("/organizations/{organization_id}/link-requests/{link_id}/accept")
async def accept_join_request(organization_id: uuid.UUID, link_id: uuid.UUID, session: Session, admin: AdminContextDep):
    """Manager accepts a farmer's own join request (farmer already consented)."""
    await _org_for_admin(session, admin, organization_id)
    await _require_manager(session, admin, organization_id)
    link = await _join_request(session, organization_id, link_id)
    link.status = "active"
    link.approved_at = datetime.now(UTC)
    _audit(session, admin, "fpo_board_join_accepted", organization_id, {"link_id": str(link.id)})
    await session.commit()
    return {"id": str(link.id), "status": link.status}


@admin_router.post("/organizations/{organization_id}/link-requests/{link_id}/reject")
async def reject_join_request(organization_id: uuid.UUID, link_id: uuid.UUID, session: Session, admin: AdminContextDep):
    await _org_for_admin(session, admin, organization_id)
    await _require_manager(session, admin, organization_id)
    link = await _join_request(session, organization_id, link_id)
    link.status = "revoked"
    link.revoked_at = datetime.now(UTC)
    _audit(session, admin, "fpo_board_join_rejected", organization_id, {"link_id": str(link.id)})
    await session.commit()
    return {"id": str(link.id), "status": link.status}


@admin_router.post("/organizations/{organization_id}/link-requests")
async def create_link_request(organization_id: uuid.UUID, body: LinkRequestIn, session: Session, admin: AdminContextDep):
    """Ask a farmer (by Farmer ID) to share their data with this FPO.

    Nothing is shared until the farmer approves in the app
    (Profile -> Organizations); they can revoke any time.
    """
    await _org_for_admin(session, admin, organization_id)
    await _require_manager(session, admin, organization_id)
    farmer = await session.scalar(select(User).where(User.farmer_ref == body.farmer_ref, User.deleted_at.is_(None)))
    if farmer is None:
        raise NotFoundError("No farmer with this Farmer ID.")
    existing = await session.scalar(
        select(OrganicPartnerFarmerLink).where(
            OrganicPartnerFarmerLink.organization_id == organization_id,
            OrganicPartnerFarmerLink.farmer_user_id == farmer.id,
        )
    )
    if existing and existing.status == JOIN_REQUESTED:
        raise ConflictError("This farmer already asked to join -- accept their request instead.")
    if existing and existing.status != "revoked":
        raise ConflictError("This farmer is already requested or linked.")
    if existing:
        existing.status = "pending"
        existing.requested_by_user_id = admin.admin.user_id
        existing.approved_at = None
        existing.revoked_at = None
        link = existing
    else:
        link = OrganicPartnerFarmerLink(
            organization_id=organization_id,
            farmer_user_id=farmer.id,
            requested_by_user_id=admin.admin.user_id,
            status="pending",
        )
        session.add(link)
    await session.flush()
    _audit(session, admin, "fpo_board_link_requested", organization_id, {"farmer_ref": body.farmer_ref})
    await session.commit()
    return {"id": str(link.id), "farmer_ref": body.farmer_ref, "status": "pending"}


@feed_router.get("")
async def feed_board(session: Session, partner: PartnerApiKeyDep):
    board = await build_board(session, partner.organization_id)
    record_partner_read(session, partner, "partner_feed_board_read", len(board.get("crops", [])))
    await session.commit()
    return board


@feed_router.get("/farmers")
async def feed_farmers(
    session: Session,
    partner: PartnerApiKeyDep,
    crop: Annotated[str | None, Query(max_length=80)] = None,
    product: Annotated[str | None, Query(max_length=160)] = None,
    need: Annotated[str | None, Query(max_length=40)] = None,
    harvest_month: Annotated[int | None, Query(ge=1, le=12)] = None,
):
    rows = await farmer_rows(
        session, partner.organization_id, crop=crop, product=product, need=need, harvest_month=harvest_month
    )
    # Machine feed = data minimisation: an API key can leak from a partner's
    # website/server, so it never carries direct identifiers. Named contact
    # details stay behind the MFA-protected staff portal.
    feed = [{k: v for k, v in row.items() if k not in FEED_REDACTED_FIELDS} for row in rows]
    record_partner_read(session, partner, "partner_feed_farmers_read", len(feed))
    await session.commit()
    return feed
