"""Integration tests for the market service (in-memory DB, fake providers)."""
from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from app.modules.auth.models import User
from app.modules.market.cache import MarketCache
from app.modules.market.exceptions import (
    FavouriteExistsError,
    FavouriteNotFoundError,
    MarketDataUnavailableError,
)
from app.modules.market.provider import (
    MockMarketProvider,
    PriceQuery,
    ProviderPrice,
)
from app.modules.market.schemas import AddFavouriteRequest, MarketPriceFilters
from app.modules.market.service import MarketService


def _today() -> date:
    return datetime.now(UTC).date()


async def _drain_refreshes(service: MarketService) -> None:
    """Wait for the service's detached background refresh tasks to finish.

    ``_ensure_fresh`` fires the provider fetch on a background task
    (``asyncio.create_task``) so the request never blocks on the provider. Tests
    await those tasks explicitly — via the strong references the service keeps in
    ``_refresh_tasks`` — so assertions run against the settled state instead of
    relying on event-loop scheduling luck.
    """
    await asyncio.gather(*service._refresh_tasks)


class FailingProvider:
    source = "failing"

    async def fetch_prices(self, query: PriceQuery) -> list[ProviderPrice]:
        raise MarketDataUnavailableError()


async def _make_user(db_session, uid: str = "fb-mkt") -> User:
    user = User(firebase_uid=uid, status="active")
    db_session.add(user)
    await db_session.flush()
    return user


def _service(db_session, *, provider=None) -> MarketService:
    return MarketService(
        db_session,
        provider=provider or MockMarketProvider(today=_today()),
        cache=MarketCache(),
    )


async def test_get_prices_fetches_persists_and_paginates(
    db_session, session_factory, monkeypatch
) -> None:
    monkeypatch.setattr(
        "app.modules.market.service.SessionLocal", session_factory
    )
    service = _service(db_session)
    # First read fires the background refresh and returns immediately (may be
    # empty); drain it, then read again to observe the persisted prices.
    await service.get_prices(MarketPriceFilters(page=1, page_size=5))
    await _drain_refreshes(service)
    result = await service.get_prices(MarketPriceFilters(page=1, page_size=5))
    assert result.total > 0
    assert result.items
    assert result.items[0].verified is True
    assert result.items[0].category  # classified


async def test_get_prices_filters_by_crop(
    db_session, session_factory, monkeypatch
) -> None:
    monkeypatch.setattr(
        "app.modules.market.service.SessionLocal", session_factory
    )
    service = _service(db_session)
    await service.get_prices(MarketPriceFilters(crop="paddy"))
    await _drain_refreshes(service)
    result = await service.get_prices(MarketPriceFilters(crop="paddy"))
    assert result.total >= 1
    assert all(item.commodity == "Paddy" for item in result.items)


async def test_today_only_excludes_older_prices(
    db_session, session_factory, monkeypatch
) -> None:
    monkeypatch.setattr(
        "app.modules.market.service.SessionLocal", session_factory
    )
    # Provider returns a single fresh row dated today.
    provider = MockMarketProvider(today=_today())
    service = _service(db_session, provider=provider)
    await service.get_prices(MarketPriceFilters(crop="paddy"), today_only=True)
    await _drain_refreshes(service)
    result = await service.get_prices(
        MarketPriceFilters(crop="paddy"), today_only=True
    )
    assert result.total >= 1
    assert all(item.price_date == _today() for item in result.items)


async def test_offline_fallback_serves_stored_prices(
    db_session, session_factory, monkeypatch
) -> None:
    monkeypatch.setattr(
        "app.modules.market.service.SessionLocal", session_factory
    )
    # First, seed the DB with a working provider (background refresh).
    good = _service(db_session)
    await good.get_prices(MarketPriceFilters(crop="paddy"))
    await _drain_refreshes(good)

    # Now a failing provider + fresh cache must still return stored prices. Its
    # background refresh fails and is swallowed; the read falls back to the rows
    # the good service already persisted.
    degraded = MarketService(
        db_session, provider=FailingProvider(), cache=MarketCache()
    )
    await degraded.get_prices(MarketPriceFilters(crop="paddy"))
    await _drain_refreshes(degraded)
    result = await degraded.get_prices(MarketPriceFilters(crop="paddy"))
    assert result.total >= 1  # graceful degradation, no exception
    assert result.items[0].verified is True
    assert result.items[0].is_stale is False
    assert result.items[0].age_days == 0


async def test_offline_fallback_labels_older_verified_price_as_stale(
    db_session, session_factory, monkeypatch
) -> None:
    monkeypatch.setattr("app.modules.market.service.SessionLocal", session_factory)
    old_day = _today() - timedelta(days=3)
    seed = _service(db_session, provider=MockMarketProvider(today=old_day))
    await seed.get_prices(MarketPriceFilters(crop="paddy"))
    await _drain_refreshes(seed)

    degraded = MarketService(
        db_session, provider=FailingProvider(), cache=MarketCache()
    )
    await degraded.get_prices(MarketPriceFilters(crop="paddy"))
    await _drain_refreshes(degraded)
    result = await degraded.get_prices(MarketPriceFilters(crop="paddy"))

    assert result.items[0].verified is True
    assert result.items[0].is_stale is True
    assert result.items[0].age_days == 3


async def test_provider_failure_can_retry_after_background_attempt_settles(
    db_session, session_factory, monkeypatch
) -> None:
    # The in-flight marker prevents duplicate concurrent calls, but a failed
    # attempt must clear it after settling so Refresh can make a real retry.
    monkeypatch.setattr(
        "app.modules.market.service.SessionLocal", session_factory
    )

    class CountingFailingProvider:
        source = "counting-failing"

        def __init__(self) -> None:
            self.calls = 0

        async def fetch_prices(self, query: PriceQuery) -> list[ProviderPrice]:
            self.calls += 1
            raise MarketDataUnavailableError()

    provider = CountingFailingProvider()
    service = MarketService(db_session, provider=provider, cache=MarketCache())
    await service.get_prices(MarketPriceFilters())
    await _drain_refreshes(service)
    assert provider.calls == 1

    await service.get_prices(MarketPriceFilters())
    await _drain_refreshes(service)
    assert provider.calls == 2


async def test_empty_provider_response_can_retry_after_attempt_settles(
    db_session, session_factory, monkeypatch
) -> None:
    monkeypatch.setattr("app.modules.market.service.SessionLocal", session_factory)

    class EmptyThenGoodProvider:
        source = "empty-then-good"

        def __init__(self) -> None:
            self.calls = 0
            self._inner = MockMarketProvider(today=_today())

        async def fetch_prices(self, query: PriceQuery) -> list[ProviderPrice]:
            self.calls += 1
            if self.calls == 1:
                return []
            return await self._inner.fetch_prices(query)

    provider = EmptyThenGoodProvider()
    service = MarketService(db_session, provider=provider, cache=MarketCache())
    first = await service.get_prices(MarketPriceFilters())
    await _drain_refreshes(service)
    assert first.items == []

    await service.get_prices(MarketPriceFilters())
    await _drain_refreshes(service)
    result = await service.get_prices(MarketPriceFilters())
    assert provider.calls == 2
    assert result.items


async def test_cache_prevents_duplicate_provider_calls(
    db_session, session_factory, monkeypatch
) -> None:
    monkeypatch.setattr(
        "app.modules.market.service.SessionLocal", session_factory
    )

    class CountingProvider:
        source = "counting"

        def __init__(self) -> None:
            self.calls = 0
            self._inner = MockMarketProvider(today=_today())

        async def fetch_prices(self, query: PriceQuery) -> list[ProviderPrice]:
            self.calls += 1
            return await self._inner.fetch_prices(query)

    provider = CountingProvider()
    service = MarketService(db_session, provider=provider, cache=MarketCache())
    await service.get_prices(MarketPriceFilters())
    await service.get_prices(MarketPriceFilters())  # same query key → cached
    await _drain_refreshes(service)  # exactly one background refresh runs
    assert provider.calls == 1


async def test_history_returns_points(db_session) -> None:
    service = _service(db_session)
    # Seed several days of history directly through the repo.
    for offset in range(3):
        day = _today() - timedelta(days=offset)
        await service.repo.save_prices(
            [
                ProviderPrice(
                    commodity="Paddy",
                    variety="Common",
                    market="Thanjavur",
                    district="Thanjavur",
                    state="Tamil Nadu",
                    minimum_price=1900 + offset,
                    maximum_price=2100 + offset,
                    modal_price=2000 + offset,
                    unit="quintal",
                    price_date=day,
                    source="mock",
                )
            ]
        )
    history = await service.get_history(
        crop="Paddy", market="Thanjavur", district=None, days=30
    )
    assert len(history.points) == 3
    assert history.market == "Thanjavur"


async def test_history_unavailable_when_no_data(db_session) -> None:
    service = MarketService(
        db_session, provider=FailingProvider(), cache=MarketCache()
    )
    with pytest.raises(MarketDataUnavailableError):
        await service.get_history(
            crop="Ragi", market="Nowhere", district=None, days=30
        )


async def test_search_returns_facets(db_session, session_factory, monkeypatch) -> None:
    monkeypatch.setattr("app.modules.market.service.SessionLocal", session_factory)
    service = _service(db_session)
    await service.search("tha")
    await _drain_refreshes(service)
    results = await service.search("tha")
    types = {r.type for r in results}
    assert "market" in types or "district" in types


async def test_favourites_add_list_and_prevent_duplicates(db_session) -> None:
    user = await _make_user(db_session)
    service = _service(db_session)
    payload = AddFavouriteRequest(
        commodity="Paddy",
        market="Thanjavur",
        district="Thanjavur",
        state="Tamil Nadu",
    )
    created = await service.add_favourite(user, payload)
    assert created.commodity == "Paddy"

    with pytest.raises(FavouriteExistsError):
        await service.add_favourite(user, payload)

    favourites = await service.list_favourites(user)
    assert len(favourites) == 1


async def test_favourite_annotated_with_latest_price(
    db_session, session_factory, monkeypatch
) -> None:
    monkeypatch.setattr("app.modules.market.service.SessionLocal", session_factory)
    user = await _make_user(db_session)
    service = _service(db_session)
    # Seed prices so the favourite has a latest price to attach.
    await service.get_prices(MarketPriceFilters(crop="paddy"))
    await _drain_refreshes(service)
    await service.add_favourite(
        user,
        AddFavouriteRequest(
            commodity="Paddy",
            market="Thanjavur",
            district="Thanjavur",
            state="Tamil Nadu",
        ),
    )
    favourites = await service.list_favourites(user)
    assert favourites[0].latest is not None
    assert favourites[0].latest.modal_price > 0


async def test_remove_favourite_and_ownership(db_session) -> None:
    owner = await _make_user(db_session, uid="fb-owner")
    other = await _make_user(db_session, uid="fb-other")
    service = _service(db_session)
    created = await service.add_favourite(
        owner,
        AddFavouriteRequest(
            commodity="Onion",
            market="Madurai",
            district="Madurai",
            state="Tamil Nadu",
        ),
    )
    # Another user cannot remove it.
    with pytest.raises(FavouriteNotFoundError):
        await service.remove_favourite(other, created.id)
    with pytest.raises(FavouriteNotFoundError):
        await service.remove_favourite(owner, uuid.uuid4())

    await service.remove_favourite(owner, created.id)
    assert await service.list_favourites(owner) == []
