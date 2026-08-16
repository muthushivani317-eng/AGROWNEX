"""Market request/response schemas (docs/API_CONTRACT.md → MARKET)."""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from pydantic import BaseModel, Field

from app.modules.market.constants import MAX_PAGE_SIZE
from app.modules.market.models import MarketFavourite, MarketPrice


class MarketPriceOut(BaseModel):
    """One current price card (docs: crop, market, district, min/max/modal…)."""

    id: uuid.UUID
    commodity: str
    variety: str
    category: str
    market: str
    district: str
    state: str
    minimum_price: float
    maximum_price: float
    modal_price: float
    unit: str
    price_date: date
    source: str
    verified: bool
    is_stale: bool
    age_days: int
    updated_at: datetime

    @classmethod
    def from_row(
        cls, price: MarketPrice, *, market: str, district: str, state: str
    ) -> MarketPriceOut:
        today = datetime.now(UTC).date()
        age_days = max(0, (today - price.price_date).days)
        return cls(
            id=price.id,
            commodity=price.commodity,
            variety=price.variety,
            category=price.category,
            market=market,
            district=district,
            state=state,
            minimum_price=price.minimum_price,
            maximum_price=price.maximum_price,
            modal_price=price.modal_price,
            unit=price.unit,
            price_date=price.price_date,
            source=price.source,
            verified=price.verified,
            is_stale=age_days > 0,
            age_days=age_days,
            updated_at=price.updated_at,
        )


class MarketHistoryPointOut(BaseModel):
    recorded_date: date
    minimum_price: float
    maximum_price: float
    modal_price: float
    unit: str


class MarketHistoryOut(BaseModel):
    commodity: str
    variety: str
    market: str
    district: str
    state: str
    unit: str
    points: list[MarketHistoryPointOut]


class MarketSearchResultOut(BaseModel):
    """A single search suggestion (crop / market / district / state)."""

    type: str
    value: str
    label: str


class FavouriteOut(BaseModel):
    id: uuid.UUID
    commodity: str
    market: str
    district: str
    state: str
    created_at: datetime
    # Latest known price for this favourite, when available.
    latest: MarketPriceOut | None = None

    @classmethod
    def from_row(
        cls, favourite: MarketFavourite, *, latest: MarketPriceOut | None = None
    ) -> FavouriteOut:
        return cls(
            id=favourite.id,
            commodity=favourite.commodity,
            market=favourite.market_name,
            district=favourite.district,
            state=favourite.state,
            created_at=favourite.created_at,
            latest=latest,
        )


class AddFavouriteRequest(BaseModel):
    commodity: str = Field(min_length=1, max_length=120)
    market: str = Field(min_length=1, max_length=160)
    district: str = Field(min_length=1, max_length=120)
    state: str = Field(min_length=1, max_length=120)


class MarketPriceFilters(BaseModel):
    """Validated query filters for GET /market and /market/today."""

    crop: str | None = Field(default=None, max_length=120)
    market: str | None = Field(default=None, max_length=160)
    district: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=MAX_PAGE_SIZE)
