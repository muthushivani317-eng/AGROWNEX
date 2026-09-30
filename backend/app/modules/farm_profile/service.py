"""Onboarding v2 persistence: profile extras, farm items, FPO/KVK join."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.admin.models import AuditLog
from app.modules.auth.models import User
from app.modules.auth.profile_models import FarmerProfile
from app.modules.farm_profile.catalog import ITEMS, item_label
from app.modules.farm_profile.models import FarmerFarmItem
from app.modules.farm_profile.schemas import ONBOARDING_FIELDS, FarmItemIn, FarmItemOut
from app.modules.organic_mvp.models import OrganicFpo, OrganicPartnerFarmerLink, OrganicPartnerOrganization

JOIN_REQUESTED = "join_requested"
MAX_OPEN_JOIN_REQUESTS = 5


def apply_onboarding_fields(profile: FarmerProfile, data) -> None:
    """Copy only the onboarding fields the client sent (see OnboardingProfileFields)."""
    for name in ONBOARDING_FIELDS:
        if name in data.model_fields_set:
            setattr(profile, name, getattr(data, name))


def item_out(row: FarmerFarmItem) -> FarmItemOut:
    out = FarmItemOut.model_validate(row)
    out.name = item_label(row.item_code, row.custom_name)
    out.name_ta = ITEMS.get(row.item_code, {}).get("ta")
    return out


async def list_items(session: AsyncSession, user_id: uuid.UUID) -> list[FarmerFarmItem]:
    return list(
        (
            await session.scalars(
                select(FarmerFarmItem)
                .where(FarmerFarmItem.user_id == user_id)
                .order_by(FarmerFarmItem.category, FarmerFarmItem.item_code, FarmerFarmItem.custom_name)
            )
        ).all()
    )


async def replace_items(session: AsyncSession, user_id: uuid.UUID, items: list[FarmItemIn]) -> list[FarmerFarmItem]:
    await session.execute(delete(FarmerFarmItem).where(FarmerFarmItem.user_id == user_id))
    session.add_all(
        [
            FarmerFarmItem(
                user_id=user_id,
                category=item.category,
                item_code=item.item_code,
                custom_name=item.custom_name,
                harvest_months=item.harvest_months,
                approx_quantity=item.approx_quantity,
                unit=item.unit,
                area_acres=item.area_acres,
                available_for_sale=item.available_for_sale,
            )
            for item in items
        ]
    )
    await session.commit()
    return await list_items(session, user_id)


async def directory(session: AsyncSession, *, kind: str | None, district: str | None) -> list[dict]:
    stmt = (
        select(OrganicPartnerOrganization, OrganicFpo.district)
        .outerjoin(OrganicFpo, OrganicFpo.id == OrganicPartnerOrganization.fpo_id)
        .where(OrganicPartnerOrganization.listed_in_app.is_(True))
    )
    if kind:
        stmt = stmt.where(OrganicPartnerOrganization.kind == kind)
    orgs = (await session.execute(stmt.order_by(OrganicPartnerOrganization.name))).all()
    wanted = (district or "").strip().lower()
    rows = [
        {"id": str(o.id), "name": o.name, "kind": o.kind, "district": o.district or fpo_district}
        for o, fpo_district in orgs
    ]
    if wanted:
        # Same-district organizations first; others still shown (a farmer may
        # belong to an FPO across the district line).
        rows.sort(key=lambda r: (0 if (r["district"] or "").strip().lower() == wanted else 1, r["name"]))
    return rows


async def request_join(session: AsyncSession, user: User, organization_id: uuid.UUID) -> dict:
    org = await session.get(OrganicPartnerOrganization, organization_id)
    if org is None or not org.listed_in_app:
        raise NotFoundError("Organization not found.")
    link = await session.scalar(
        select(OrganicPartnerFarmerLink).where(
            OrganicPartnerFarmerLink.organization_id == organization_id,
            OrganicPartnerFarmerLink.farmer_user_id == user.id,
        )
    )
    if link and link.status == "active":
        raise ConflictError("You are already a member of this organization.")
    if link and link.status == JOIN_REQUESTED:
        raise ConflictError("Your request is already waiting for approval.")

    if link and link.status == "pending":
        # The organization already asked for this farmer: joining = approving.
        link.status = "active"
        link.approved_at = datetime.now(UTC)
        action = "organic_partner_link_approved"
    else:
        open_requests = await session.scalar(
            select(func.count()).where(
                OrganicPartnerFarmerLink.farmer_user_id == user.id,
                OrganicPartnerFarmerLink.status == JOIN_REQUESTED,
            )
        )
        if (open_requests or 0) >= MAX_OPEN_JOIN_REQUESTS:
            raise ConflictError("Too many requests waiting. Cancel one before sending another.")
        if link is None:
            link = OrganicPartnerFarmerLink(organization_id=organization_id, farmer_user_id=user.id, requested_by_user_id=user.id)
            session.add(link)
        link.status = JOIN_REQUESTED
        link.requested_by_user_id = user.id
        link.approved_at = None
        link.revoked_at = None
        action = "organic_partner_join_requested"
    await session.flush()
    session.add(
        AuditLog(
            role="farmer",
            action=action,
            target="organic_partner_farmer_link",
            target_id=str(link.id),
            meta={"actor_user_id": str(user.id), "organization_id": str(organization_id), "consent": True},
        )
    )
    await session.commit()
    return {"id": str(link.id), "organization_id": str(organization_id), "organization_name": org.name, "status": link.status}
