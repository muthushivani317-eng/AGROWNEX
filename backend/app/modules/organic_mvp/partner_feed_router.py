"""Read-only external data feed for a partner organization's own website.

Auth: `X-Partner-Api-Key` header (see partner_api_auth.py). Every route below
is scoped to `partner.organization_id`, which is resolved from the API key
alone -- no route accepts an organization id as input, so a key can never be
used to reach another organization's farmers, whatever is passed in the URL.

Scope, by design (docs/AGROWAI_PROJECT_STATE business-model notes):
- INCLUDED: farmer identification (farmer_ref, district/block/village, crop)
  and agronomic monitoring signals (disease detections, disease-risk alerts,
  basic farm facts) -- what an FPO needs to support and monitor its members.
- EXCLUDED, always: anything from Sell My Produce / procurement / buyer
  listings / prices / commissions, financial services, subscriptions, or
  B2B/government contracts. This router never imports from those modules.
- Only farmers with an ACTIVE consent link to the calling organization are
  ever returned (organic_mvp.OrganicPartnerFarmerLink.status == "active") --
  a farmer who has not approved, or has revoked, the link is invisible here.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import NotFoundError
from app.modules.auth.models import User
from app.modules.disease.models import DiseaseReport
from app.modules.disease_risk.models import DiseaseRiskAlert
from app.modules.farms.models import Farm
from app.modules.organic_mvp.models import OrganicPartnerFarmerLink
from app.modules.organic_mvp.partner_api_auth import PartnerApiKeyDep

router = APIRouter(prefix="/partner-feed", tags=["partner-feed"])
Session = Annotated[AsyncSession, Depends(get_session)]


def _linked_farmers_query(organization_id: uuid.UUID):
    return (
        select(User)
        .join(OrganicPartnerFarmerLink, OrganicPartnerFarmerLink.farmer_user_id == User.id)
        .where(
            OrganicPartnerFarmerLink.organization_id == organization_id,
            OrganicPartnerFarmerLink.status == "active",
            User.deleted_at.is_(None),
        )
    )


@router.get("/farmers")
async def list_farmers(
    session: Session,
    partner: PartnerApiKeyDep,
    limit: Annotated[int, Query(le=200, ge=1)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    rows = (
        await session.scalars(
            _linked_farmers_query(partner.organization_id)
            .order_by(User.farmer_ref)
            .limit(limit)
            .offset(offset)
        )
    ).all()
    farms_by_user: dict[uuid.UUID, list[Farm]] = {}
    if rows:
        user_ids = [row.id for row in rows]
        farms = (
            await session.scalars(
                select(Farm).where(Farm.user_id.in_(user_ids), Farm.deleted_at.is_(None))
            )
        ).all()
        for farm in farms:
            farms_by_user.setdefault(farm.user_id, []).append(farm)
    return {
        "organization": partner.organization_name,
        "count": len(rows),
        "farmers": [
            {
                "farmer_ref": row.farmer_ref,
                "farms": [
                    {"crop": farm.crop, "area_hectares": farm.area_hectares, "status": farm.status}
                    for farm in farms_by_user.get(row.id, [])
                ],
            }
            for row in rows
        ],
    }


async def _farmer_or_404(session: AsyncSession, organization_id: uuid.UUID, farmer_ref: str) -> User:
    farmer = await session.scalar(
        _linked_farmers_query(organization_id).where(User.farmer_ref == farmer_ref)
    )
    if farmer is None:
        # Deliberately the same 404 whether farmer_ref does not exist at all,
        # belongs to another organization, or was revoked -- never confirm
        # to a caller that a given farmer_ref exists elsewhere.
        raise NotFoundError("Farmer not found among this organization's linked farmers.")
    return farmer


@router.get("/farmers/{farmer_ref}/summary")
async def farmer_summary(farmer_ref: str, session: Session, partner: PartnerApiKeyDep):
    farmer = await _farmer_or_404(session, partner.organization_id, farmer_ref)
    farms = (
        await session.scalars(select(Farm).where(Farm.user_id == farmer.id, Farm.deleted_at.is_(None)))
    ).all()
    reports = (
        await session.scalars(
            select(DiseaseReport)
            .where(DiseaseReport.user_id == farmer.id)
            .order_by(DiseaseReport.created_at.desc())
            .limit(20)
        )
    ).all()
    alerts = (
        await session.scalars(
            select(DiseaseRiskAlert)
            .where(DiseaseRiskAlert.user_id == farmer.id)
            .order_by(DiseaseRiskAlert.generated_at.desc())
            .limit(20)
        )
    ).all()
    return {
        "farmer_ref": farmer.farmer_ref,
        "farms": [
            {
                "name": farm.name,
                "crop": farm.crop,
                "crop_variety": farm.crop_variety,
                "area_hectares": farm.area_hectares,
                "status": farm.status,
            }
            for farm in farms
        ],
        "disease_reports": [
            {
                "crop": r.crop,
                "disease": r.disease,
                "confidence": r.confidence,
                "severity": r.severity,
                "needs_expert_review": r.needs_expert_review,
                "created_at": r.created_at.isoformat(),
            }
            for r in reports
        ],
        "disease_risk_alerts": [
            {
                "crop": a.crop,
                "disease_key": a.disease_key,
                "status": a.status,
                "risk_level": a.risk_level,
                "generated_at": a.generated_at.isoformat(),
            }
            for a in alerts
        ],
    }
