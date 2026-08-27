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

import asyncio
import uuid
from datetime import timedelta
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.core.timezone import today_ist
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


class _RefreshOutcome(StrEnum):
    """Internal result of one upstream refresh attempt.

    An empty list can be a valid provider response, so callers must not infer
    provider health from the number of records returned.
    """

    SUCCESS = "success"
    UNAVAILABLE = "unavailable"


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
        # Strong references to detached background refresh tasks. Without this
        # the event loop only weakly references a bare ``create_task`` result,
        # so the refresh could be garbage-collected mid-flight (see asyncio docs).
        self._refresh_tasks: set[asyncio.Task[_RefreshOutcome]] = set()
        self._refresh_tasks_by_key: dict[str, asyncio.Task[_RefreshOutcome]] = {}
        self._refresh_outcomes_by_key: dict[str, _RefreshOutcome] = {}

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
        refresh_started = await self._ensure_fresh(query)

        # India Standard Time, not UTC (docs: app.core.timezone) -- this is a
        # "what day is it for the farmer" boundary, not an event timestamp.
        on_date = today_ist() if today_only else None
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
        refresh_outcome: _RefreshOutcome | None = None
        if not rows and refresh_started:
            key = self.cache.key(query)
            refresh_task = self._refresh_tasks_by_key.get(key)
            if refresh_task is not None:
                # Give the just-started background refresh a chance to land real
                # data before we respond -- but never hold the HTTP response
                # hostage to the full external-provider retry budget (Agmarknet:
                # up to AGMARKNET_MAX_RETRIES x AGMARKNET_TIMEOUT_SECONDS ~= 24s
                # worst case). `_ensure_fresh`'s own docstring promises "the
                # request never waits on the external provider" -- unconditionally
                # awaiting the task here broke that promise for exactly the worst
                # case (a farmer's very first request for a given filter combo),
                # producing the ~20s blank-then-client-timeout the Market Prices
                # screen was showing live (reported 2026-08-17: client gave up
                # after ~19.9s with a 499, one retry later succeeded in <100ms
                # once the background fetch had landed).
                #
                # The first fix capped this wait at 3s, which avoided that timeout
                # but traded it for a *more common* problem (reported 2026-08-19):
                # a single successful Agmarknet call routinely takes close to the
                # full AGMARKNET_TIMEOUT_SECONDS (8s), so any first-time filter
                # combo not already warmed by the 2-hour favourites cron (e.g. a
                # farmer's own district on the "Nearby" tab, or a crop nobody has
                # favourited yet) would almost always still be empty at the 3s
                # mark -- the farmer saw a "not found" empty state on a totally
                # ordinary, successful fetch that just hadn't landed yet. 8.5s
                # covers one full Agmarknet attempt (plus its JSON parse) with
                # margin, while staying well inside the mobile client's 20s
                # request timeout (``EXPO_PUBLIC_API_TIMEOUT_MS``) even after
                # response transit and serialization overhead. `asyncio.shield`
                # keeps the refresh running even after we stop waiting on it, so
                # a genuinely slow/down provider still isn't wasted work -- the
                # next request (or a manual pull-to-refresh) for this filter
                # combo benefits once it lands.
                try:
                    refresh_outcome = await asyncio.wait_for(
                        asyncio.shield(refresh_task), timeout=8.5
                    )
                except TimeoutError:
                    refresh_outcome = _RefreshOutcome.UNAVAILABLE
                else:
                    rows, total = await self.repo.list_prices(
                        crop=filters.crop,
                        market=filters.market,
                        district=filters.district,
                        state=filters.state,
                        on_date=on_date,
                        limit=filters.page_size,
                        offset=offset,
                    )
            else:
                # A very fast provider failure can finish between
                # ``_ensure_fresh`` returning and this lookup. Its completion
                # callback preserves the typed outcome after removing the task.
                refresh_outcome = self._refresh_outcomes_by_key.pop(key, None)
        elif not rows and total == 0 and self.cache.get(self.cache.key(query)) == "refreshing":
            # The shared Redis/in-memory cache can contain an in-flight marker
            # created by another request or process. This service has no local
            # task/outcome to await, so the provider state is still unknown.
            # Do not turn that uncertainty into a misleading successful empty
            # response; verified stored rows above remain available.
            refresh_outcome = _RefreshOutcome.UNAVAILABLE
        # Mandi publications can arrive after midnight. The "Today" view should
        # remain useful on those days by showing the most recent reported market
        # date instead of incorrectly presenting an empty result.
        if today_only and not rows:
            latest_date = await self.repo.latest_price_date(
                crop=filters.crop,
                market=filters.market,
                district=filters.district,
                state=filters.state,
            )
            if latest_date is not None:
                rows, total = await self.repo.list_prices(
                    crop=filters.crop,
                    market=filters.market,
                    district=filters.district,
                    state=filters.state,
                    on_date=latest_date,
                    limit=filters.page_size,
                    offset=offset,
                )
        # No stored verified fallback and the provider attempt failed (or did
        # not finish within the bounded request wait): surface a retryable
        # outage instead of misrepresenting the failure as a genuine zero-match
        # response. A completed successful provider call that returned [] keeps
        # the normal empty-page semantics.
        if not rows and refresh_outcome is _RefreshOutcome.UNAVAILABLE:
            raise MarketDataUnavailableError()
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

    async def _ensure_fresh(self, query: PriceQuery) -> bool:
        """Schedule a provider refresh without blocking the response on it.

        The request never waits on the external provider. If the query is
        already marked fresh in the cache, nothing happens. Otherwise the cache
        key is marked fresh *before* the background task starts, so concurrent
        requests for the same query don't pile into the provider, and the
        provider refresh is fired off with :func:`asyncio.create_task` and left
        to run detached — the caller returns immediately and reads are served
        from whatever is already stored in the DB.

        Blocking here would expose the caller to the provider's full retry
        budget (e.g. a timing-out Agmarknet), exceeding the client's request
        timeout and leaving the screen stuck on the error state. The existing
        2-hour cron job (:mod:`app.modules.market.jobs`) keeps favourited
        targets broadly fresh; this background refresh catches ad-hoc queries
        the cron hasn't seen yet.
        """
        key = self.cache.key(query)
        if self.cache.get(key) is not None:
            return False
        self._refresh_outcomes_by_key.pop(key, None)
        self.cache.set(key, "refreshing")
        task = asyncio.create_task(self._background_refresh(query))
        self._refresh_tasks.add(task)
        self._refresh_tasks_by_key[key] = task

        def _record_completion(completed: asyncio.Task[_RefreshOutcome]) -> None:
            self._refresh_tasks.discard(completed)
            if self._refresh_tasks_by_key.get(key) is completed:
                self._refresh_tasks_by_key.pop(key, None)
            try:
                self._refresh_outcomes_by_key[key] = completed.result()
            except (asyncio.CancelledError, Exception):
                # `_background_refresh` normally translates all provider/runtime
                # failures. This final guard still fails closed if cancellation
                # or an unexpected callback boundary escapes it.
                self._refresh_outcomes_by_key[key] = _RefreshOutcome.UNAVAILABLE

        task.add_done_callback(_record_completion)
        return True

    async def _background_refresh(self, query: PriceQuery) -> _RefreshOutcome:
        """Fetch + store prices for ``query`` on a detached background task.

        Runs its own DB session because this task may still be running after the
        original request's session (``self.session``) is closed — the same
        session-per-job idiom as :func:`app.worker._run`. All exceptions are
        handled internally: an unhandled one would only surface later as a
        "Task exception was never retrieved" warning, since the task runs
        detached via :func:`asyncio.create_task`.
        """
        async with SessionLocal() as session:
            key = self.cache.key(query)
            try:
                service = MarketService(session, provider=self.provider)
                records = await service._fetch_and_store(query)
                await session.commit()
                # A zero-row response is not fresh market data. Remove the
                # optimistic in-flight marker so a later manual/app retry can
                # ask the provider again instead of serving an empty page for
                # the full cache TTL.
                if not records:
                    self.cache.delete(key)
                else:
                    self.cache.set(key, "fresh")
                return _RefreshOutcome.SUCCESS
            except MarketDataUnavailableError:
                self.cache.delete(key)
                logger.info("market background refresh unavailable for query")
                return _RefreshOutcome.UNAVAILABLE
            except Exception:
                await session.rollback()
                self.cache.delete(key)
                logger.exception("market background refresh failed")
                return _RefreshOutcome.UNAVAILABLE

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

        # India Standard Time, not UTC (docs: app.core.timezone).
        date_from = today_ist() - timedelta(days=days)
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
