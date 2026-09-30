"""Onboarding v2 persistence: profile extras, farm items, FPO/KVK join."""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.admin.models import AuditLog
from app.modules.auth.models import User
from app.modules.auth.profile_models import FarmerProfile
from app.modules.farm_profile.catalog import APP_ITEM_ALIASES_REVERSE, ITEMS, item_label
from app.modules.farm_profile.models import FarmerFarmItem
from app.modules.farm_profile.schemas import (
    ONBOARDING_FIELDS,
    AppFarmProductIn,
    AppFarmProductOut,
    FarmItemIn,
    FarmItemOut,
)
from app.modules.organic_mvp.models import OrganicFpo, OrganicPartnerFarmerLink, OrganicPartnerOrganization

JOIN_REQUESTED = "join_requested"
MAX_OPEN_JOIN_REQUESTS = 5


def apply_onboarding_fields(profile: FarmerProfile, data) -> None:
    """Copy only the onboarding fields the client sent (see OnboardingProfileFields)."""
    for name in ONBOARDING_FIELDS:
        if name in data.model_fields_set:
            value = getattr(data, name)
            if name.startswith("wants_") and value is None:
                continue
            setattr(profile, name, value)


async def apply_app_farm_products(session: AsyncSession, user_id: uuid.UUID, data) -> None:
    """Store the app's ``farm_products`` (PUT /farmers/me) as farm items.

    Only when the client sent the field; the list replaces the farmer's items.
    """
    products: list[AppFarmProductIn] | None = getattr(data, "farm_products", None)
    if products is None or "farm_products" not in data.model_fields_set:
        return
    items: dict[tuple[str, str], FarmItemIn] = {}
    for product in products:
        item = product.to_item()
        items[(item.item_code, (item.custom_name or "").lower())] = item  # last one wins
    await _replace_rows(session, user_id, list(items.values()))


def app_products_out(rows: list[FarmerFarmItem], today: date | None = None) -> list[AppFarmProductOut]:
    """Farm items in the app's ``farm_products`` shape (next harvest month as YYYY-MM)."""
    today = today or date.today()
    out = []
    for row in rows:
        month = None
        if row.harvest_months:
            upcoming = [m for m in row.harvest_months if m >= today.month]
            m = upcoming[0] if upcoming else row.harvest_months[0]
            month = f"{today.year + (0 if upcoming else 1)}-{m:02d}"
        is_other = row.item_code not in ITEMS
        out.append(
            AppFarmProductOut(
                product_id=(row.custom_name or "other") if is_other else APP_ITEM_ALIASES_REVERSE.get(row.item_code, row.item_code),
                category=row.category,
                expected_harvest_month=month,
                approximate_quantity=row.approx_quantity,
                unit="count" if row.unit in ("nos", "head") else row.unit,
                available_for_sale=row.available_for_sale,
            )
        )
    return out


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
    await _replace_rows(session, user_id, items)
    await session.commit()
    return await list_items(session, user_id)


async def _replace_rows(session: AsyncSession, user_id: uuid.UUID, items: list[FarmItemIn]) -> None:
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
    await session.flush()


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
