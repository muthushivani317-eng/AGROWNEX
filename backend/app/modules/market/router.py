"""Market API routes (docs/API_CONTRACT.md → MARKET).

    GET    /market                 (current prices; filter + paginate)
    GET    /market/today           (today's prices)
    GET    /market/history         (historical prices for a crop + market)
    GET    /market/search          (crop / market / district / state suggestions)
    GET    /market/favourites      (the farmer's saved markets + latest price)
    POST   /market/favourites      (add a favourite)
    DELETE /market/favourites/{id} (remove a favourite)
    GET    /market/sync-status     (price freshness; no personal data)
    POST   /market/backup/ingest   (official report upload; ingest token)

Thin routes — filtering, provider orchestration, caching and offline fallback
live in ``MarketService``. Every response uses the global envelope.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.market.backup import (
    BackupIngestIn,
    BackupIngestOut,
    SyncStatusOut,
    ingest_state_report,
    sync_status,
    verify_ingest_token,
)
from app.modules.market.constants import DEFAULT_HISTORY_DAYS, MAX_HISTORY_DAYS
from app.modules.market.dependencies import CurrentUser, MarketServiceDep
from app.modules.market.schemas import (
    AddFavouriteRequest,
    FavouriteOut,
    MarketHistoryOut,
    MarketPriceFilters,
    MarketPriceOut,
    MarketSearchResultOut,
)
from app.schemas.response import PaginatedData, SuccessResponse, success

router = APIRouter(prefix="/market", tags=["market"])

CropQuery = Query(None, max_length=120, description="Filter by commodity/crop")
MarketQuery = Query(None, max_length=160, description="Filter by market/mandi")
DistrictQuery = Query(None, max_length=120, description="Filter by district")
StateQuery = Query(None, max_length=120, description="Filter by state")


@router.get("", response_model=SuccessResponse[PaginatedData[MarketPriceOut]])
async def list_prices(
    current_user: CurrentUser,
    service: MarketServiceDep,
    crop: str | None = CropQuery,
    market: str | None = MarketQuery,
    district: str | None = DistrictQuery,
    state: str | None = StateQuery,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Current mandi prices, filterable by crop/market/district/state."""
    filters = MarketPriceFilters(
        crop=crop,
        market=market,
        district=district,
        state=state,
        page=page,
        page_size=page_size,
    )
    data = await service.get_prices(filters)
    return success(data)


@router.get("/today", response_model=SuccessResponse[PaginatedData[MarketPriceOut]])
async def today_prices(
    current_user: CurrentUser,
    service: MarketServiceDep,
    crop: str | None = CropQuery,
    market: str | None = MarketQuery,
    district: str | None = DistrictQuery,
    state: str | None = StateQuery,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Only today's prices (docs: today's price)."""
    filters = MarketPriceFilters(
        crop=crop,
        market=market,
        district=district,
        state=state,
        page=page,
        page_size=page_size,
    )
    data = await service.get_prices(filters, today_only=True)
    return success(data)


@router.get("/history", response_model=SuccessResponse[MarketHistoryOut])
async def price_history(
    current_user: CurrentUser,
    service: MarketServiceDep,
    crop: str = Query(..., max_length=120),
    market: str = Query(..., max_length=160),
    district: str | None = DistrictQuery,
    days: int = Query(DEFAULT_HISTORY_DAYS, ge=1, le=MAX_HISTORY_DAYS),
):
    """Historical modal/min/max prices for a crop at a market."""
    data = await service.get_history(
        crop=crop, market=market, district=district, days=days
    )
    return success(data)


@router.get("/search", response_model=SuccessResponse[list[MarketSearchResultOut]])
async def search(
    current_user: CurrentUser,
    service: MarketServiceDep,
    q: str = Query(..., min_length=1, max_length=120),
    limit: int = Query(20, ge=1, le=50),
):
    """Search crops, markets, districts and states."""
    results = await service.search(q, limit=limit)
    return success(results)


@router.get("/favourites", response_model=SuccessResponse[list[FavouriteOut]])
async def list_favourites(
    current_user: CurrentUser,
    service: MarketServiceDep,
):
    """The farmer's saved markets, each annotated with the latest known price."""
    data = await service.list_favourites(current_user)
    return success(data)


@router.post(
    "/favourites",
    response_model=SuccessResponse[FavouriteOut],
    status_code=status.HTTP_201_CREATED,
)
async def add_favourite(
    payload: AddFavouriteRequest,
    current_user: CurrentUser,
    service: MarketServiceDep,
):
    """Add a market + commodity to favourites."""
    data = await service.add_favourite(current_user, payload)
    return success(data, message="Added to favourites")


@router.delete(
    "/favourites/{favourite_id}", response_model=SuccessResponse[None]
)
async def remove_favourite(
    favourite_id: uuid.UUID,
    current_user: CurrentUser,
    service: MarketServiceDep,
):
    """Remove a favourite market."""
    await service.remove_favourite(current_user, favourite_id)
    return success(None, message="Removed from favourites")


SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("/sync-status", response_model=SuccessResponse[SyncStatusOut])
async def market_sync_status(
    session: SessionDep,
    state: str = Query("Tamil Nadu", min_length=2, max_length=60),
):
    """How fresh the stored prices are (read by the backup uploader and the
    nightly check). Aggregate counts only — no personal data."""
    return success(await sync_status(session, state=state))


@router.post("/backup/ingest", response_model=SuccessResponse[BackupIngestOut])
async def backup_ingest(
    payload: BackupIngestIn,
    session: SessionDep,
    x_market_ingest_token: Annotated[str | None, Header()] = None,
):
    """Store one official Agmarknet 2.0 state report uploaded from India."""
    verify_ingest_token(x_market_ingest_token)
    return success(await ingest_state_report(session, payload), message="Prices stored")
