"""Integration tests for the market repository (in-memory DB)."""
from __future__ import annotations

from datetime import date

from app.modules.market.models import MarketFavourite
from app.modules.market.provider import ProviderPrice
from app.modules.market.repository import MarketRepository


def _price(**overrides: object) -> ProviderPrice:
    base = dict(
        commodity="Paddy",
        variety="Common",
        market="Thanjavur",
        district="Thanjavur",
        state="Tamil Nadu",
        minimum_price=1980.0,
        maximum_price=2120.0,
        modal_price=2050.0,
        unit="quintal",
        price_date=date(2026, 7, 11),
        source="mock",
    )
    base.update(overrides)
    return ProviderPrice(**base)  # type: ignore[arg-type]


async def test_upsert_creates_location_price_and_history(db_session) -> None:
    repo = MarketRepository(db_session)
    price = await repo.upsert_price(_price())

    assert price.category == "cereal"  # classified from commodity
    location = await repo.get_or_create_location(
        market_name="Thanjavur", district="Thanjavur", state="Tamil Nadu"
    )
    assert price.market_id == location.id

    _, history = await repo.history(
        commodity="Paddy", market="Thanjavur", district=None, date_from=date(2026, 1, 1)
    )
    assert len(history) == 1
    assert history[0].modal_price == 2050.0


async def test_upsert_is_idempotent_for_same_day(db_session) -> None:
    repo = MarketRepository(db_session)
    await repo.upsert_price(_price())
    await repo.upsert_price(_price(modal_price=2075.0))  # same market/commodity/day

    rows, total = await repo.list_prices(crop="paddy")
    assert total == 1
    assert rows[0][0].modal_price == 2075.0  # updated in place, not duplicated


async def test_list_prices_filters_and_paginates(db_session) -> None:
    repo = MarketRepository(db_session)
    await repo.save_prices(
        [
            _price(commodity="Paddy", market="Thanjavur"),
            _price(commodity="Tomato", market="Coimbatore", district="Coimbatore"),
            _price(commodity="Onion", market="Madurai", district="Madurai"),
        ]
    )

    rows, total = await repo.list_prices(crop="tomato")
    assert total == 1 and rows[0][0].commodity == "Tomato"

    page1, total_all = await repo.list_prices(limit=2, offset=0)
    assert total_all == 3 and len(page1) == 2
    page2, _ = await repo.list_prices(limit=2, offset=2)
    assert len(page2) == 1


async def test_list_prices_today_only(db_session) -> None:
    repo = MarketRepository(db_session)
    await repo.save_prices(
        [
            _price(price_date=date(2026, 7, 11)),
            _price(variety="Old", price_date=date(2026, 7, 1)),
        ]
    )
    rows, total = await repo.list_prices(on_date=date(2026, 7, 11))
    assert total == 1


async def test_search_returns_distinct_facets(db_session) -> None:
    repo = MarketRepository(db_session)
    await repo.save_prices(
        [_price(commodity="Paddy"), _price(commodity="Tomato", market="Coimbatore")]
    )
    commodities, markets, districts, states = await repo.search("tha")
    assert "Thanjavur" in markets
    assert "Thanjavur" in districts
    commodities2, *_ = await repo.search("pad")
    assert "Paddy" in commodities2


async def test_favourite_crud(db_session) -> None:
    repo = MarketRepository(db_session)
    from app.modules.auth.models import User

    user = User(firebase_uid="fb-mkt-1", status="active")
    db_session.add(user)
    await db_session.flush()

    fav = await repo.add_favourite(
        MarketFavourite(
            user_id=user.id,
            commodity="Paddy",
            market_name="Thanjavur",
            district="Thanjavur",
            state="Tamil Nadu",
        )
    )
    assert (await repo.list_favourites(user.id))[0].id == fav.id
    found = await repo.find_favourite(
        user.id, commodity="Paddy", market="Thanjavur", district="Thanjavur"
    )
    assert found is not None

    await repo.soft_delete_favourite(fav)
    assert await repo.list_favourites(user.id) == []
