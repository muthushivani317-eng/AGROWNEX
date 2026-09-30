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
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.modules.admin.constants import AdminPermission, AdminRole
from app.modules.admin.dependencies import AdminContextDep
from app.modules.admin.models import AuditLog
from app.modules.auth.models import User
from app.modules.fpo_board.service import build_board, farmer_rows, rows_to_csv
from app.modules.organic_mvp.models import (
    OrganicPartnerFarmerLink,
    OrganicPartnerOrganization,
    OrganicPartnerStaff,
)
from app.modules.organic_mvp.partner_api_auth import PartnerApiKeyDep
from app.modules.organic_mvp.partner_router import LinkRequestIn

admin_router = APIRouter(prefix="/admin/fpo-board", tags=["fpo-board"])
feed_router = APIRouter(prefix="/partner-feed/crop-board", tags=["partner-feed"])
Session = Annotated[AsyncSession, Depends(get_session)]
PLATFORM_ROLES = {AdminRole.OWNER.value, AdminRole.SUPER_ADMIN.value}


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
    counts = dict(
        (
            await session.execute(
                select(OrganicPartnerFarmerLink.organization_id, func.count())
                .where(OrganicPartnerFarmerLink.status == "active")
                .group_by(OrganicPartnerFarmerLink.organization_id)
            )
        ).all()
    )
    return [
        {"id": str(o.id), "name": o.name, "kind": o.kind, "farmer_count": counts.get(o.id, 0)}
        for o in organizations
    ]


@admin_router.get("/organizations/{organization_id}")
async def organization_board(organization_id: uuid.UUID, session: Session, admin: AdminContextDep):
    organization = await _org_for_admin(session, admin, organization_id)
    board = await build_board(session, organization_id)
    return {"organization": {"id": str(organization.id), "name": organization.name, "kind": organization.kind}, **board}


@admin_router.get("/organizations/{organization_id}/farmers")
async def organization_farmer_list(
    organization_id: uuid.UUID,
    session: Session,
    admin: AdminContextDep,
    crop: Annotated[str | None, Query(max_length=80)] = None,
    product: Annotated[str | None, Query(max_length=160)] = None,
):
    await _org_for_admin(session, admin, organization_id)
    rows = await farmer_rows(session, organization_id, crop=crop, product=product)
    _audit(session, admin, "fpo_board_farmers_viewed", organization_id, {"crop": crop, "product": product, "rows": len(rows)})
    await session.commit()
    return rows


@admin_router.get("/organizations/{organization_id}/farmers.csv")
async def organization_farmer_csv(
    organization_id: uuid.UUID,
    session: Session,
    admin: AdminContextDep,
    crop: Annotated[str | None, Query(max_length=80)] = None,
    product: Annotated[str | None, Query(max_length=160)] = None,
):
    organization = await _org_for_admin(session, admin, organization_id)
    rows = await farmer_rows(session, organization_id, crop=crop, product=product)
    _audit(session, admin, "fpo_board_farmers_exported", organization_id, {"crop": crop, "product": product, "rows": len(rows)})
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
        raise ForbiddenError("Only the FPO manager can add farmers.")


@admin_router.get("/organizations/{organization_id}/link-requests")
async def list_link_requests(organization_id: uuid.UUID, session: Session, admin: AdminContextDep):
    """Farmer links for this FPO. Only the farmer ID is shown -- a farmer's
    details appear on the board only after they approve in the app."""
    await _org_for_admin(session, admin, organization_id)
    rows = (
        await session.execute(
            select(OrganicPartnerFarmerLink, User.farmer_ref)
            .join(User, User.id == OrganicPartnerFarmerLink.farmer_user_id)
            .where(OrganicPartnerFarmerLink.organization_id == organization_id)
            .order_by(OrganicPartnerFarmerLink.created_at.desc())
            .limit(500)
        )
    ).all()
    return [
        {
            "id": str(link.id),
            "farmer_ref": farmer_ref,
            "status": link.status,
            "requested_at": link.created_at,
            "approved_at": link.approved_at,
            "revoked_at": link.revoked_at,
        }
        for link, farmer_ref in rows
    ]


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
    return await build_board(session, partner.organization_id)


@feed_router.get("/farmers")
async def feed_farmers(
    session: Session,
    partner: PartnerApiKeyDep,
    crop: Annotated[str | None, Query(max_length=80)] = None,
    product: Annotated[str | None, Query(max_length=160)] = None,
):
    return await farmer_rows(session, partner.organization_id, crop=crop, product=product)
