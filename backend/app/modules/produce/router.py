"""Produce API routes (docs/API_CONTRACT.md → PRODUCE).

    GET    /produce             (list the farmer's offers; filter + paginate)
    POST   /produce             (create a verified future-harvest offer)
    GET    /produce/upcoming     (still-relevant harvests, soonest first)
    GET    /produce/history      (concluded offers)
    GET    /produce/{id}         (full detail + procurement insight)
    PUT    /produce/{id}         (partial update)
    DELETE /produce/{id}         (soft delete)
    POST   /produce/{id}/images  (attach an uploaded image)

Thin routes — validation, ownership, the snapshot, the Procurement Engine and
provider routing all live in ``ProduceService``. Static routes are declared
before ``/{offer_id}``. All endpoints are authenticated.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.modules.produce.constants import ProduceAvailabilityType, ProduceCategory, ProduceStatus
from app.modules.produce.dependencies import CurrentUser, ProduceServiceDep
from app.modules.produce.schemas import (
    FarmerOfferDecisionIn,
    FrozenBuyerOfferOut,
    ProduceImageIn,
    ProduceListFilters,
    ProduceOfferCreate,
    ProduceOfferDetailOut,
    ProduceOfferSummaryOut,
    ProduceOfferUpdate,
)
from app.schemas.response import PaginatedData, SuccessResponse, success

router = APIRouter(prefix="/produce", tags=["produce"])


def _page_out(page, insights, organic=None) -> PaginatedData[ProduceOfferSummaryOut]:
    organic = organic or {}
    return PaginatedData(
        items=[
            ProduceOfferSummaryOut.from_offer(
                o,
                insight=insights.get(o.id),
                organic_certification_status=organic.get(o.id, (None, False))[0],
                organic_certification_verified=organic.get(o.id, (None, False))[1],
            )
            for o in page.items
        ],
        page=page.page,
        page_size=page.page_size,
        total=page.total,
        total_pages=page.total_pages,
    )


@router.get("", response_model=SuccessResponse[PaginatedData[ProduceOfferSummaryOut]])
async def list_produce(
    current_user: CurrentUser,
    service: ProduceServiceDep,
    status_filter: ProduceStatus | None = Query(None, alias="status"),
    crop: str | None = Query(None, max_length=80),
    farm_id: uuid.UUID | None = Query(None),
    category: ProduceCategory | None = Query(None),
    availability_type: ProduceAvailabilityType | None = Query(None),
    search: str | None = Query(None, max_length=120),
    organic_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List the farmer's produce offers, filterable by status/crop/farm/search.
    organic_only restricts to farms with a currently-verified organic
    certificate (never a self-claim -- see OrganicFarmProfile.certification_status)."""
    filters = ProduceListFilters(
        status=status_filter,
        crop=crop,
        farm_id=farm_id,
        category=category,
        availability_type=availability_type,
        search=search,
        organic_only=organic_only,
        page=page,
        page_size=page_size,
    )
    page_data, insights, organic = await service.list_offers(current_user, filters)
    return success(_page_out(page_data, insights, organic))


@router.post(
    "",
    response_model=SuccessResponse[ProduceOfferDetailOut],
    status_code=status.HTTP_201_CREATED,
)
async def create_produce(
    payload: ProduceOfferCreate,
    current_user: CurrentUser,
    service: ProduceServiceDep,
):
    """Create a verified future-harvest offer (collected for procurement planning)."""
    offer = await service.create_offer(current_user, payload)
    _, insight, (organic_status, organic_verified) = await service.get_offer(
        current_user, offer.id
    )
    return success(
        ProduceOfferDetailOut.from_offer_detail(
            offer,
            insight=insight,
            organic_certification_status=organic_status,
            organic_certification_verified=organic_verified,
        ),
        message="Produce offer created",
    )


@router.get(
    "/upcoming",
    response_model=SuccessResponse[PaginatedData[ProduceOfferSummaryOut]],
)
async def upcoming_harvests(
    current_user: CurrentUser,
    service: ProduceServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Still-relevant harvests due today or later, soonest first."""
    page_data, insights, organic = await service.upcoming(current_user, page=page, page_size=page_size)
    return success(_page_out(page_data, insights, organic))


@router.get(
    "/history",
    response_model=SuccessResponse[PaginatedData[ProduceOfferSummaryOut]],
)
async def produce_history(
    current_user: CurrentUser,
    service: ProduceServiceDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Concluded offers (harvested / fulfilled / withdrawn / expired)."""
    page_data, insights, organic = await service.history(current_user, page=page, page_size=page_size)
    return success(_page_out(page_data, insights, organic))


@router.get("/{offer_id}", response_model=SuccessResponse[ProduceOfferDetailOut])
async def get_produce(
    offer_id: uuid.UUID,
    current_user: CurrentUser,
    service: ProduceServiceDep,
):
    """Full offer detail with the deterministic procurement insight."""
    offer, insight, (organic_status, organic_verified) = await service.get_offer(
        current_user, offer_id
    )
    return success(
        ProduceOfferDetailOut.from_offer_detail(
            offer,
            insight=insight,
            organic_certification_status=organic_status,
            organic_certification_verified=organic_verified,
        )
    )


def _frozen_offer_out(case, decision=None) -> FrozenBuyerOfferOut:
    return FrozenBuyerOfferOut(
        offer_id=case.offer_id,
        case_id=case.id,
        status=case.status,
        terms_hash=case.frozen_terms_hash,
        frozen_at=case.frozen_at,
        terms=case.frozen_terms,
        decision=getattr(decision, "decision", None),
        decided_at=getattr(decision, "decided_at", None),
    )


@router.get("/{offer_id}/buyer-offer", response_model=SuccessResponse[FrozenBuyerOfferOut])
async def get_frozen_buyer_offer(
    offer_id: uuid.UUID, current_user: CurrentUser, service: ProduceServiceDep
):
    case, decision = await service.frozen_buyer_offer(current_user, offer_id)
    return success(_frozen_offer_out(case, decision))


@router.post(
    "/{offer_id}/buyer-offer/decision", response_model=SuccessResponse[FrozenBuyerOfferOut]
)
async def decide_frozen_buyer_offer(
    offer_id: uuid.UUID,
    payload: FarmerOfferDecisionIn,
    current_user: CurrentUser,
    service: ProduceServiceDep,
):
    case, decision = await service.decide_buyer_offer(current_user, offer_id, payload)
    return success(_frozen_offer_out(case, decision), message="Farmer decision recorded")


@router.put("/{offer_id}", response_model=SuccessResponse[ProduceOfferDetailOut])
async def update_produce(
    offer_id: uuid.UUID,
    payload: ProduceOfferUpdate,
    current_user: CurrentUser,
    service: ProduceServiceDep,
):
    """Partially update an offer (re-freezes the snapshot if crop/district change)."""
    offer, insight = await service.update_offer(current_user, offer_id, payload)
    return success(
        ProduceOfferDetailOut.from_offer_detail(offer, insight=insight),
        message="Produce offer updated",
    )


@router.delete("/{offer_id}", response_model=SuccessResponse[None])
async def delete_produce(
    offer_id: uuid.UUID,
    current_user: CurrentUser,
    service: ProduceServiceDep,
):
    """Soft-delete an offer."""
    await service.delete_offer(current_user, offer_id)
    return success(None, message="Produce offer removed")


@router.post(
    "/{offer_id}/images",
    response_model=SuccessResponse[ProduceOfferDetailOut],
    status_code=status.HTTP_201_CREATED,
)
async def add_produce_image(
    offer_id: uuid.UUID,
    payload: ProduceImageIn,
    current_user: CurrentUser,
    service: ProduceServiceDep,
):
    """Attach an uploaded image (S3/R2 URL + metadata) to an offer."""
    offer, _ = await service.add_image(current_user, offer_id, payload)
    _, insight, (organic_status, organic_verified) = await service.get_offer(
        current_user, offer_id
    )
    return success(
        ProduceOfferDetailOut.from_offer_detail(
            offer,
            insight=insight,
            organic_certification_status=organic_status,
            organic_certification_verified=organic_verified,
        ),
        message="Image added",
    )
