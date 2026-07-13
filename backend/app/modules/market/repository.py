"""Market repository (docs/BACKEND_ARCHITECTURE.md → Repository Pattern).

The only layer that queries the market tables. Handles upserts from the provider
(locations + current prices + history), the offline-fallback reads, favourites
CRUD, and the distinct-value search facets. No SQL lives in routes or services.
"""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.market.constants import LocationStatus, classify_commodity
from app.modules.market.models import (
    MarketFavourite,
    MarketLocation,
    MarketPrice,
    MarketPriceHistory,
)
from app.modules.market.provider import ProviderPrice


class MarketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ----------------------------------------------------------------- #
    # Locations
    # ----------------------------------------------------------------- #
    async def get_or_create_location(
        self, *, market_name: str, district: str, state: str
    ) -> MarketLocation:
        result = await self.session.execute(
            select(MarketLocation).where(
                MarketLocation.market_name == market_name,
                MarketLocation.district == district,
                MarketLocation.state == state,
            )
        )
        location = result.scalar_one_or_none()
        if location is not None:
            return location
        location = MarketLocation(
            market_name=market_name,
            district=district,
            state=state,
            status=LocationStatus.ACTIVE.value,
        )
        self.session.add(location)
        await self.session.flush()
        return location

    async def location_map(
        self, location_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, MarketLocation]:
        if not location_ids:
            return {}
        result = await self.session.execute(
            select(MarketLocation).where(MarketLocation.id.in_(location_ids))
        )
        return {loc.id: loc for loc in result.scalars().all()}

    # ----------------------------------------------------------------- #
    # Prices (upsert current + append history)
    # ----------------------------------------------------------------- #
    async def upsert_price(self, record: ProviderPrice) -> MarketPrice:
        location = await self.get_or_create_location(
            market_name=record.market, district=record.district, state=record.state
        )
        result = await self.session.execute(
            select(MarketPrice).where(
                MarketPrice.market_id == location.id,
                MarketPrice.commodity == record.commodity,
                MarketPrice.variety == record.variety,
                MarketPrice.price_date == record.price_date,
            )
        )
        price = result.scalar_one_or_none()
        category = classify_commodity(record.commodity).value
        if price is None:
            price = MarketPrice(
                market_id=location.id,
                commodity=record.commodity,
                variety=record.variety,
                grade=record.grade,
                category=category,
                minimum_price=record.minimum_price,
                maximum_price=record.maximum_price,
                modal_price=record.modal_price,
                unit=record.unit,
                price_date=record.price_date,
                source=record.source,
                verified=True,
            )
            self.session.add(price)
        else:
            price.minimum_price = record.minimum_price
            price.maximum_price = record.maximum_price
            price.modal_price = record.modal_price
            price.unit = record.unit
            price.grade = record.grade
            price.category = category
            price.source = record.source
        await self.session.flush()
        await self._record_history(location.id, record)
        return price

    async def _record_history(
        self, market_id: uuid.UUID, record: ProviderPrice
    ) -> None:
        result = await self.session.execute(
            select(MarketPriceHistory).where(
                MarketPriceHistory.market_id == market_id,
                MarketPriceHistory.commodity == record.commodity,
                MarketPriceHistory.variety == record.variety,
                MarketPriceHistory.recorded_date == record.price_date,
            )
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            existing.minimum_price = record.minimum_price
            existing.maximum_price = record.maximum_price
            existing.modal_price = record.modal_price
            existing.unit = record.unit
            return
        self.session.add(
            MarketPriceHistory(
                market_id=market_id,
                commodity=record.commodity,
                variety=record.variety,
                minimum_price=record.minimum_price,
                maximum_price=record.maximum_price,
                modal_price=record.modal_price,
                unit=record.unit,
                recorded_date=record.price_date,
                source=record.source,
            )
        )

    async def save_prices(self, records: list[ProviderPrice]) -> list[MarketPrice]:
        saved = [await self.upsert_price(record) for record in records]
        return saved

    # ----------------------------------------------------------------- #
    # Reads (offline fallback + today)
    # ----------------------------------------------------------------- #
    def _price_filter(
        self,
        *,
        crop: str | None = None,
        market: str | None = None,
        district: str | None = None,
        state: str | None = None,
        on_date: date | None = None,
    ) -> Select[tuple[MarketPrice, MarketLocation]]:
        stmt = select(MarketPrice, MarketLocation).join(
            MarketLocation, MarketPrice.market_id == MarketLocation.id
        )
        if crop:
            stmt = stmt.where(func.lower(MarketPrice.commodity).like(f"%{crop.lower()}%"))
        if market:
            stmt = stmt.where(
                func.lower(MarketLocation.market_name).like(f"%{market.lower()}%")
            )
        if district:
            stmt = stmt.where(
                func.lower(MarketLocation.district).like(f"%{district.lower()}%")
            )
        if state:
            stmt = stmt.where(
                func.lower(MarketLocation.state).like(f"%{state.lower()}%")
            )
        if on_date is not None:
            stmt = stmt.where(MarketPrice.price_date == on_date)
        return stmt

    async def list_prices(
        self,
        *,
        crop: str | None = None,
        market: str | None = None,
        district: str | None = None,
        state: str | None = None,
        on_date: date | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[tuple[MarketPrice, MarketLocation]], int]:
        base = self._price_filter(
            crop=crop, market=market, district=district, state=state, on_date=on_date
        )
        count_stmt = select(func.count()).select_from(base.subquery())
        total = int((await self.session.execute(count_stmt)).scalar_one())

        page_stmt = (
            base.order_by(
                MarketPrice.price_date.desc(),
                MarketPrice.commodity.asc(),
                MarketLocation.market_name.asc(),
            )
            .limit(limit)
            .offset(offset)
        )
        rows = list((await self.session.execute(page_stmt)).all())
        return [(row[0], row[1]) for row in rows], total

    async def latest_price(
        self, *, commodity: str, market: str, district: str
    ) -> tuple[MarketPrice, MarketLocation] | None:
        stmt = (
            self._price_filter(crop=commodity, market=market, district=district)
            .order_by(MarketPrice.price_date.desc())
            .limit(1)
        )
        row = (await self.session.execute(stmt)).first()
        return (row[0], row[1]) if row else None

    async def history(
        self,
        *,
        commodity: str,
        market: str,
        district: str | None,
        date_from: date,
    ) -> tuple[MarketLocation | None, list[MarketPriceHistory]]:
        loc_stmt = select(MarketLocation).where(
            func.lower(MarketLocation.market_name).like(f"%{market.lower()}%")
        )
        if district:
            loc_stmt = loc_stmt.where(
                func.lower(MarketLocation.district).like(f"%{district.lower()}%")
            )
        location = (await self.session.execute(loc_stmt.limit(1))).scalar_one_or_none()
        if location is None:
            return None, []
        hist_stmt = (
            select(MarketPriceHistory)
            .where(
                MarketPriceHistory.market_id == location.id,
                func.lower(MarketPriceHistory.commodity).like(f"%{commodity.lower()}%"),
                MarketPriceHistory.recorded_date >= date_from,
            )
            .order_by(MarketPriceHistory.recorded_date.asc())
        )
        points = list((await self.session.execute(hist_stmt)).scalars().all())
        return location, points

    # ----------------------------------------------------------------- #
    # Search facets
    # ----------------------------------------------------------------- #
    async def search(
        self, term: str, *, limit: int = 20
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        like = f"%{term.lower()}%"

        commodities = (
            await self.session.execute(
                select(MarketPrice.commodity)
                .where(func.lower(MarketPrice.commodity).like(like))
                .distinct()
                .limit(limit)
            )
        ).scalars().all()
        markets = (
            await self.session.execute(
                select(MarketLocation.market_name)
                .where(func.lower(MarketLocation.market_name).like(like))
                .distinct()
                .limit(limit)
            )
        ).scalars().all()
        districts = (
            await self.session.execute(
                select(MarketLocation.district)
                .where(func.lower(MarketLocation.district).like(like))
                .distinct()
                .limit(limit)
            )
        ).scalars().all()
        states = (
            await self.session.execute(
                select(MarketLocation.state)
                .where(func.lower(MarketLocation.state).like(like))
                .distinct()
                .limit(limit)
            )
        ).scalars().all()
        return list(commodities), list(markets), list(districts), list(states)

    # ----------------------------------------------------------------- #
    # Favourites (user-scoped)
    # ----------------------------------------------------------------- #
    async def list_favourites(self, user_id: uuid.UUID) -> list[MarketFavourite]:
        result = await self.session.execute(
            select(MarketFavourite)
            .where(
                MarketFavourite.user_id == user_id,
                MarketFavourite.is_deleted.is_(False),
            )
            .order_by(MarketFavourite.created_at.desc())
        )
        return list(result.scalars().all())

    async def distinct_favourite_targets(
        self,
    ) -> list[tuple[str, str | None, str | None, str | None]]:
        """Distinct (commodity, market, district, state) across all farmers'
        favourites — the set of prices the background scheduler keeps fresh."""
        result = await self.session.execute(
            select(
                MarketFavourite.commodity,
                MarketFavourite.market_name,
                MarketFavourite.district,
                MarketFavourite.state,
            )
            .where(MarketFavourite.is_deleted.is_(False))
            .distinct()
        )
        return [tuple(row) for row in result.all()]

    async def find_favourite(
        self, user_id: uuid.UUID, *, commodity: str, market: str, district: str
    ) -> MarketFavourite | None:
        result = await self.session.execute(
            select(MarketFavourite).where(
                MarketFavourite.user_id == user_id,
                MarketFavourite.commodity == commodity,
                MarketFavourite.market_name == market,
                MarketFavourite.district == district,
                MarketFavourite.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def get_favourite(
        self, favourite_id: uuid.UUID, user_id: uuid.UUID
    ) -> MarketFavourite | None:
        result = await self.session.execute(
            select(MarketFavourite).where(
                MarketFavourite.id == favourite_id,
                MarketFavourite.user_id == user_id,
                MarketFavourite.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def add_favourite(self, favourite: MarketFavourite) -> MarketFavourite:
        self.session.add(favourite)
        await self.session.flush()
        return favourite

    async def soft_delete_favourite(self, favourite: MarketFavourite) -> None:
        favourite.is_deleted = True
        await self.session.flush()
