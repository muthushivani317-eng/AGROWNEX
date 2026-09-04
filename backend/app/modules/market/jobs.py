"""Market background jobs (Phase 3 — ARQ worker).

Pure orchestration over the existing service/repository so it is unit-testable
with a mocked provider (no network). Wired into the ARQ worker on a schedule.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.farms.repositories import FarmRepository
from app.modules.market.exceptions import MarketDataUnavailableError
from app.modules.market.provider import MarketPriceProvider
from app.modules.market.repository import MarketRepository
from app.modules.market.schemas import MarketPriceFilters
from app.modules.market.service import MarketService

logger = get_logger("market.jobs")


async def refresh_market_prices(
    session: AsyncSession, *, provider: MarketPriceProvider | None = None
) -> dict[str, int]:
    """Refresh every commodity/market farmers actually track: explicit
    favourites, plus every active farm's own crop + district, upserting current
    prices + history via the provider, cache bypassed.

    Favourites alone under-cover a small/growing user base -- most farmers
    haven't favourited anything yet, so most of what they actually look at
    (their own crop, their own district) was previously only ever fetched
    live, on demand, competing with a slow upstream provider (docs: 2026-09
    market reliability investigation)."""
    repo = MarketRepository(session)
    farm_repo = FarmRepository(session)
    favourite_targets = await repo.distinct_favourite_targets()
    farm_targets = [
        (crop, None, district, None)
        for crop, district in await farm_repo.distinct_crop_district_targets()
    ]
    targets = list({*favourite_targets, *farm_targets})
    service = MarketService(session, provider=provider)

    refreshed_prices = 0
    refreshed_targets = 0
    for commodity, market, district, state in targets:
        try:
            count = await service.refresh(
                MarketPriceFilters(
                    crop=commodity, market=market, district=district, state=state
                )
            )
        except MarketDataUnavailableError:
            logger.info("market refresh skipped (provider unavailable): %s", commodity)
            continue
        refreshed_targets += 1
        refreshed_prices += count

    logger.info(
        "market refresh: %s/%s targets, %s prices",
        refreshed_targets,
        len(targets),
        refreshed_prices,
    )
    return {
        "targets": len(targets),
        "refreshed_targets": refreshed_targets,
        "prices": refreshed_prices,
    }
