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
from app.core.exceptions import ForbiddenError, NotFoundError
from app.modules.admin.constants import AdminPermission, AdminRole
from app.modules.admin.dependencies import AdminContextDep
from app.modules.admin.models import AuditLog
from app.modules.fpo_board.service import build_board, farmer_rows, rows_to_csv
from app.modules.organic_mvp.models import (
    OrganicPartnerFarmerLink,
    OrganicPartnerOrganization,
    OrganicPartnerStaff,
)
from app.modules.organic_mvp.partner_api_auth import PartnerApiKeyDep

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
