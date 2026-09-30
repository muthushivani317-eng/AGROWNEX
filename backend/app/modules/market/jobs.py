"""Market background jobs (Phase 3 — ARQ worker).

Pure orchestration over the existing service/repository so it is unit-testable
with a mocked provider (no network). Wired into the ARQ worker on a schedule.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.farms.repositories import FarmRepository
from app.modules.market.agmarknet_v2 import AgmarknetV2Provider
from app.modules.market.constants import (
    AGMARKNET_SYNC_MAX_PAGES,
    AGMARKNET_SYNC_MAX_RETRIES,
    AGMARKNET_SYNC_TIMEOUT_SECONDS,
    DATA_GOV_API_KEY,
    MARKET_SYNC_STATES,
)
from app.modules.market.exceptions import MarketDataUnavailableError
from app.modules.market.provider import (
    AgmarknetProvider,
    FallbackMarketProvider,
    MarketPriceProvider,
    official_providers,
)
from app.modules.market.repository import MarketRepository
from app.modules.market.schemas import MarketPriceFilters
from app.modules.market.service import MarketService

logger = get_logger("market.jobs")


def _sync_sources() -> list[MarketPriceProvider]:
    """Official sources with the worker's generous timeout/retry budget."""
    return official_providers(
        agmarknet=AgmarknetProvider(
            timeout=AGMARKNET_SYNC_TIMEOUT_SECONDS, max_retries=AGMARKNET_SYNC_MAX_RETRIES
        )
        if DATA_GOV_API_KEY
        else None,
        agmarknet_v2=AgmarknetV2Provider(max_retries=AGMARKNET_SYNC_MAX_RETRIES),
    )


def _sync_provider() -> MarketPriceProvider | None:
    """Per-crop refresh: data.gov.in first, Agmarknet 2.0 when it is unavailable."""
    sources = _sync_sources()
    if not sources:
        return None
    return sources[0] if len(sources) == 1 else FallbackMarketProvider(*sources)


async def refresh_market_prices(
    session: AsyncSession,
    *,
    provider: MarketPriceProvider | None = None,
    sync_states: tuple[str, ...] = MARKET_SYNC_STATES,
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
    service = MarketService(session, provider=provider or _sync_provider())

    # State-wide sync first: the app serves these stored prices, so a slow or
    # briefly-down source never reaches the farmer's screen. Every official
    # source is synced (not just the first that answers) so one source being
    # down never leaves the state without fresh prices.
    sync_sources = [provider] if provider is not None else _sync_sources()
    synced_states = 0
    synced_prices = 0
    for state in sync_states:
        state_ok = False
        for source in sync_sources:
            try:
                count = await MarketService(session, provider=source).sync_state(
                    state, max_pages=AGMARKNET_SYNC_MAX_PAGES
                )
            except MarketDataUnavailableError:
                logger.info(
                    "market state sync skipped (%s unavailable): %s",
                    getattr(source, "source", "provider"),
                    state,
                )
                await session.rollback()
                continue
            await session.commit()
            state_ok = True
            synced_prices += count
            logger.info(
                "market state sync: %s via %s -> %s prices",
                state,
                getattr(source, "source", "provider"),
                count,
            )
        if state_ok:
            synced_states += 1

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
        "synced_states": synced_states,
        "synced_prices": synced_prices,
    }
