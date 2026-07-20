"""Integration tests for the market service (in-memory DB, fake providers)."""
from __future__ import annotations

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


async def test_get_prices_fetches_persists_and_paginates(db_session) -> None:
    service = _service(db_session)
    result = await service.get_prices(MarketPriceFilters(page=1, page_size=5))
    assert result.total > 0
    assert result.items
    assert result.items[0].verified is True
    assert result.items[0].category  # classified


async def test_get_prices_filters_by_crop(db_session) -> None:
    service = _service(db_session)
    result = await service.get_prices(MarketPriceFilters(crop="paddy"))
    assert result.total >= 1
    assert all(item.commodity == "Paddy" for item in result.items)


async def test_today_only_excludes_older_prices(db_session) -> None:
    # Provider returns a single fresh row dated today.
    provider = MockMarketProvider(today=_today())
    service = _service(db_session, provider=provider)
    result = await service.get_prices(
        MarketPriceFilters(crop="paddy"), today_only=True
    )
    assert result.total >= 1
    assert all(item.price_date == _today() for item in result.items)


async def test_offline_fallback_serves_stored_prices(db_session) -> None:
    # First, seed the DB with a working provider.
    good = _service(db_session)
    await good.get_prices(MarketPriceFilters(crop="paddy"))

    # Now a failing provider + fresh cache must still return stored prices.
    degraded = MarketService(
        db_session, provider=FailingProvider(), cache=MarketCache()
    )
    result = await degraded.get_prices(MarketPriceFilters(crop="paddy"))
    assert result.total >= 1  # graceful degradation, no exception


async def test_provider_failure_is_cached_to_avoid_retry_storm(db_session) -> None:
    # A timing-out / failing provider must be marked fresh after the first read
    # so it is not re-hit on every request (which would make each response block
    # on the full retry budget and exceed the client timeout).
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
    await service.get_prices(MarketPriceFilters())  # same key → served from cache
    assert provider.calls == 1


async def test_cache_prevents_duplicate_provider_calls(db_session) -> None:
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


async def test_search_returns_facets(db_session) -> None:
    service = _service(db_session)
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


async def test_favourite_annotated_with_latest_price(db_session) -> None:
    user = await _make_user(db_session)
    service = _service(db_session)
    # Seed prices so the favourite has a latest price to attach.
    await service.get_prices(MarketPriceFilters(crop="paddy"))
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
