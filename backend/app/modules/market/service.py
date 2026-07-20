"""Market service (docs/BACKEND_ARCHITECTURE.md → API → Service → Repository).

Orchestrates the price flow:

    cache → provider (fetch + normalize) → repository (persist current + history)
          → cache set → response

On a provider timeout/failure the service degrades gracefully to the last prices
stored in the database (offline fallback). ``refresh`` is the same path with the
cache bypassed — the hook a background scheduler calls to keep prices fresh.
Business logic lives here; routes stay thin and no SQL runs outside the repo.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.auth.models import User
from app.modules.market.cache import MarketCache, market_cache
from app.modules.market.constants import (
    DEFAULT_HISTORY_DAYS,
    MAX_HISTORY_DAYS,
    MarketSearchType,
    classify_commodity,
)
from app.modules.market.exceptions import (
    FavouriteExistsError,
    FavouriteNotFoundError,
    MarketDataUnavailableError,
)
from app.modules.market.models import MarketFavourite
from app.modules.market.provider import (
    MarketPriceProvider,
    PriceQuery,
    ProviderPrice,
    get_default_provider,
)
from app.modules.market.repository import MarketRepository
from app.modules.market.schemas import (
    AddFavouriteRequest,
    FavouriteOut,
    MarketHistoryOut,
    MarketHistoryPointOut,
    MarketPriceFilters,
    MarketPriceOut,
    MarketSearchResultOut,
)
from app.schemas.response import PaginatedData

logger = get_logger("market.service")


class MarketService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        provider: MarketPriceProvider | None = None,
        cache: MarketCache | None = None,
    ) -> None:
        self.session = session
        self.repo = MarketRepository(session)
        self.provider = provider or get_default_provider()
        self.cache = cache or market_cache

    # ----------------------------------------------------------------- #
    # Current prices
    # ----------------------------------------------------------------- #
    async def get_prices(
        self, filters: MarketPriceFilters, *, today_only: bool = False
    ) -> PaginatedData[MarketPriceOut]:
        query = PriceQuery(
            commodity=filters.crop,
            market=filters.market,
            district=filters.district,
            state=filters.state,
        )
        await self._ensure_fresh(query)

        on_date = datetime.now(UTC).date() if today_only else None
        offset = (filters.page - 1) * filters.page_size
        rows, total = await self.repo.list_prices(
            crop=filters.crop,
            market=filters.market,
            district=filters.district,
            state=filters.state,
            on_date=on_date,
            limit=filters.page_size,
            offset=offset,
        )
        items = [
            MarketPriceOut.from_row(
                price, market=loc.market_name, district=loc.district, state=loc.state
            )
            for price, loc in rows
        ]
        total_pages = (total + filters.page_size - 1) // filters.page_size if total else 0
        return PaginatedData(
            items=items,
            page=filters.page,
            page_size=filters.page_size,
            total=total,
            total_pages=total_pages,
        )

    async def refresh(self, filters: MarketPriceFilters) -> int:
        """Force a provider fetch + persist, bypassing the cache (scheduler hook)."""
        query = PriceQuery(
            commodity=filters.crop,
            market=filters.market,
            district=filters.district,
            state=filters.state,
        )
        records = await self._fetch_and_store(query)
        return len(records)

    async def _ensure_fresh(self, query: PriceQuery) -> None:
        """Populate the DB from the provider unless a fresh cache entry exists.

        A provider failure is non-fatal: reads fall back to stored prices. The
        freshness marker is set on *both* outcomes (fetched or gracefully
        unavailable) so a timing-out upstream (e.g. Agmarknet) is not re-hit on
        every request — otherwise each read would block on the full retry budget
        and exceed the client's request timeout, leaving the screen stuck on the
        error state. Stored prices are served until the cache TTL expires.
        Unexpected errors still propagate uncached.
        """
        key = self.cache.key(query)
        if self.cache.get(key) is not None:
            return
        try:
            await self._fetch_and_store(query)
        except MarketDataUnavailableError:
            logger.info("market provider unavailable; serving stored prices")
        self.cache.set(key, True)

    async def _fetch_and_store(self, query: PriceQuery) -> list[ProviderPrice]:
        records = await self.provider.fetch_prices(query)
        if records:
            await self.repo.save_prices(records)
        return records

    # ----------------------------------------------------------------- #
    # History
    # ----------------------------------------------------------------- #
    async def get_history(
        self, *, crop: str, market: str, district: str | None, days: int
    ) -> MarketHistoryOut:
        days = max(1, min(days or DEFAULT_HISTORY_DAYS, MAX_HISTORY_DAYS))
        # Best-effort refresh so today's point is present; ignore provider errors.
        try:
            await self._fetch_and_store(
                PriceQuery(commodity=crop, market=market, district=district)
            )
        except MarketDataUnavailableError:
            pass

        date_from = datetime.now(UTC).date() - timedelta(days=days)
        location, points = await self.repo.history(
            commodity=crop, market=market, district=district, date_from=date_from
        )
        if location is None or not points:
            raise MarketDataUnavailableError()
        return MarketHistoryOut(
            commodity=crop,
            variety=points[-1].variety,
            market=location.market_name,
            district=location.district,
            state=location.state,
            unit=points[-1].unit,
            points=[
                MarketHistoryPointOut(
                    recorded_date=point.recorded_date,
                    minimum_price=point.minimum_price,
                    maximum_price=point.maximum_price,
                    modal_price=point.modal_price,
                    unit=point.unit,
                )
                for point in points
            ],
        )

    # ----------------------------------------------------------------- #
    # Search
    # ----------------------------------------------------------------- #
    async def search(self, term: str, *, limit: int = 20) -> list[MarketSearchResultOut]:
        term = term.strip()
        if not term:
            return []
        # Seed the DB (best-effort) with the broad catalog so search matches across
        # every facet — crops, markets, districts and states — not just commodities.
        try:
            await self._ensure_fresh(PriceQuery())
        except MarketDataUnavailableError:
            pass
        commodities, markets, districts, states = await self.repo.search(
            term, limit=limit
        )
        results: list[MarketSearchResultOut] = []
        for value in commodities:
            results.append(
                MarketSearchResultOut(
                    type=MarketSearchType.CROP.value, value=value, label=value
                )
            )
        for value in markets:
            results.append(
                MarketSearchResultOut(
                    type=MarketSearchType.MARKET.value, value=value, label=value
                )
            )
        for value in districts:
            results.append(
                MarketSearchResultOut(
                    type=MarketSearchType.DISTRICT.value, value=value, label=value
                )
            )
        for value in states:
            results.append(
                MarketSearchResultOut(
                    type=MarketSearchType.STATE.value, value=value, label=value
                )
            )
        return results

    # ----------------------------------------------------------------- #
    # Favourites
    # ----------------------------------------------------------------- #
    async def list_favourites(self, user: User) -> list[FavouriteOut]:
        favourites = await self.repo.list_favourites(user.id)
        out: list[FavouriteOut] = []
        for favourite in favourites:
            latest = await self.repo.latest_price(
                commodity=favourite.commodity,
                market=favourite.market_name,
                district=favourite.district,
            )
            latest_out = (
                MarketPriceOut.from_row(
                    latest[0],
                    market=latest[1].market_name,
                    district=latest[1].district,
                    state=latest[1].state,
                )
                if latest
                else None
            )
            out.append(FavouriteOut.from_row(favourite, latest=latest_out))
        return out

    async def add_favourite(
        self, user: User, payload: AddFavouriteRequest
    ) -> FavouriteOut:
        existing = await self.repo.find_favourite(
            user.id,
            commodity=payload.commodity,
            market=payload.market,
            district=payload.district,
        )
        if existing is not None:
            raise FavouriteExistsError()
        favourite = await self.repo.add_favourite(
            MarketFavourite(
                user_id=user.id,
                commodity=payload.commodity,
                market_name=payload.market,
                district=payload.district,
                state=payload.state,
            )
        )
        return FavouriteOut.from_row(favourite)

    async def remove_favourite(self, user: User, favourite_id: uuid.UUID) -> None:
        favourite = await self.repo.get_favourite(favourite_id, user.id)
        if favourite is None:
            raise FavouriteNotFoundError()
        await self.repo.soft_delete_favourite(favourite)

    # Kept for parity with the docs' commodity classification helper.
    @staticmethod
    def category_for(commodity: str) -> str:
        return classify_commodity(commodity).value
