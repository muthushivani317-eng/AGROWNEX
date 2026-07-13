"""Scheme API routes (docs/API_CONTRACT.md → GOVERNMENT SCHEMES).

    GET    /schemes                 (all verified schemes; filter + paginate)
    GET    /schemes/eligible        (eligible schemes ranked by score)
    GET    /schemes/recommended     (top-ranked eligible schemes)
    GET    /schemes/bookmarks       (the farmer's bookmarked schemes)
    POST   /schemes/bookmarks       (bookmark a scheme)
    DELETE /schemes/bookmarks/{id}  (remove a bookmark)
    GET    /schemes/{id}            (full detail + eligibility for the farmer)

Thin routes — seeding, context building, the eligibility engine and ranking all
live in ``SchemeService``. Static routes are declared before ``/{scheme_id}``.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.modules.schemes.constants import FarmerCategory
from app.modules.schemes.dependencies import CurrentUser, SchemeServiceDep
from app.modules.schemes.schemas import (
    BookmarkRequest,
    EligibilityQuery,
    EligibleSchemesOut,
    RecommendedSchemesOut,
    SchemeDetailOut,
    SchemeSummaryOut,
)
from app.schemas.response import PaginatedData, SuccessResponse, success

router = APIRouter(prefix="/schemes", tags=["schemes"])

FarmIdQuery = Query(None, description="Use a specific farm's crop/land/district")
StateQuery = Query(None, max_length=80)
DistrictQuery = Query(None, max_length=80)
CropQuery = Query(None, max_length=80)
LandQuery = Query(None, ge=0, le=100000, description="Land size in hectares")
IncomeQuery = Query(None, ge=0, description="Annual income in ₹")
CategoryQuery = Query(None, description="Override the derived farmer category")


def _query(
    farm_id: uuid.UUID | None,
    state: str | None,
    district: str | None,
    crop: str | None,
    land_hectares: float | None,
    annual_income: int | None,
    farmer_category: FarmerCategory | None,
) -> EligibilityQuery:
    return EligibilityQuery(
        farm_id=farm_id,
        state=state,
        district=district,
        crop=crop,
        land_hectares=land_hectares,
        annual_income=annual_income,
        farmer_category=farmer_category,
    )


@router.get(
    "", response_model=SuccessResponse[PaginatedData[SchemeSummaryOut]]
)
async def list_schemes(
    current_user: CurrentUser,
    service: SchemeServiceDep,
    category: str | None = Query(None, max_length=30),
    state: str | None = StateQuery,
    crop: str | None = CropQuery,
    search: str | None = Query(None, max_length=120),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """All verified schemes, filterable by category/state/crop/search."""
    data = await service.list_all(
        current_user,
        category=category,
        state=state,
        crop=crop,
        search=search,
        page=page,
        page_size=page_size,
    )
    return success(data)


@router.get("/eligible", response_model=SuccessResponse[EligibleSchemesOut])
async def eligible_schemes(
    current_user: CurrentUser,
    service: SchemeServiceDep,
    farm_id: uuid.UUID | None = FarmIdQuery,
    state: str | None = StateQuery,
    district: str | None = DistrictQuery,
    crop: str | None = CropQuery,
    land_hectares: float | None = LandQuery,
    annual_income: int | None = IncomeQuery,
    farmer_category: FarmerCategory | None = CategoryQuery,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Schemes the farmer is eligible (or likely eligible) for, ranked by score."""
    query = _query(
        farm_id, state, district, crop, land_hectares, annual_income, farmer_category
    )
    results, context = await service.eligible(
        current_user, query, page=page, page_size=page_size
    )
    return success(EligibleSchemesOut(results=results, context=context))


@router.get("/recommended", response_model=SuccessResponse[RecommendedSchemesOut])
async def recommended_schemes(
    current_user: CurrentUser,
    service: SchemeServiceDep,
    farm_id: uuid.UUID | None = FarmIdQuery,
    state: str | None = StateQuery,
    district: str | None = DistrictQuery,
    crop: str | None = CropQuery,
    land_hectares: float | None = LandQuery,
    annual_income: int | None = IncomeQuery,
    farmer_category: FarmerCategory | None = CategoryQuery,
):
    """The highest-scoring eligible schemes for the farmer."""
    query = _query(
        farm_id, state, district, crop, land_hectares, annual_income, farmer_category
    )
    items, context = await service.recommended(current_user, query)
    return success(RecommendedSchemesOut(items=items, context=context))


@router.get("/bookmarks", response_model=SuccessResponse[list[SchemeSummaryOut]])
async def list_bookmarks(
    current_user: CurrentUser,
    service: SchemeServiceDep,
):
    """The farmer's bookmarked schemes (with their current eligibility)."""
    items = await service.list_bookmarks(current_user)
    return success(items)


@router.post(
    "/bookmarks",
    response_model=SuccessResponse[None],
    status_code=status.HTTP_201_CREATED,
)
async def add_bookmark(
    payload: BookmarkRequest,
    current_user: CurrentUser,
    service: SchemeServiceDep,
):
    """Bookmark a scheme."""
    await service.add_bookmark(current_user, payload.scheme_id)
    return success(None, message="Scheme bookmarked")


@router.delete(
    "/bookmarks/{scheme_id}", response_model=SuccessResponse[None]
)
async def remove_bookmark(
    scheme_id: uuid.UUID,
    current_user: CurrentUser,
    service: SchemeServiceDep,
):
    """Remove a bookmarked scheme."""
    await service.remove_bookmark(current_user, scheme_id)
    return success(None, message="Bookmark removed")


@router.get("/{scheme_id}", response_model=SuccessResponse[SchemeDetailOut])
async def get_scheme(
    scheme_id: uuid.UUID,
    current_user: CurrentUser,
    service: SchemeServiceDep,
    farm_id: uuid.UUID | None = FarmIdQuery,
):
    """Full scheme detail with the farmer's eligibility, documents and steps."""
    query = EligibilityQuery(farm_id=farm_id)
    detail = await service.get_detail(current_user, scheme_id, query)
    return success(detail)
