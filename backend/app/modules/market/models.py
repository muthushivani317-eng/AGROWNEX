"""Market ORM models (docs/DATABASE_SCHEMA.md → Market domain).

Four tables:

* ``market_locations``     — master list of mandis (upserted from the provider).
* ``market_prices``        — current price per market + commodity + variety.
* ``market_price_history`` — daily historical snapshots for trend charts.
* ``market_favourites``    — a farmer's saved markets (user-scoped).

The schema documents ``crop_id`` on price rows, but AgrowAI has no crops master
table yet and the verified external source (Agmarknet) returns the commodity as
free text. Commodity/variety are therefore stored as text on the price rows —
faithful to the real data source (docs/PRODUCT_RULES.md → never fabricate market
data) and forward-compatible with a future crops master.
"""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import (
    Boolean,
    Date,
    Float,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.market.constants import (
    CommodityCategory,
    LocationStatus,
    PriceUnit,
)
from app.shared.base_model import (
    GUID,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)


class MarketLocation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "market_locations"
    __table_args__ = (
        UniqueConstraint(
            "market_name", "district", "state", name="uq_market_location"
        ),
    )

    market_name: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    district: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    state: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    block: Mapped[str | None] = mapped_column(String(120))
    village: Mapped[str | None] = mapped_column(String(120))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(
        String(12), default=LocationStatus.ACTIVE.value, nullable=False
    )


class MarketPrice(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "market_prices"
    __table_args__ = (
        UniqueConstraint(
            "market_id",
            "commodity",
            "variety",
            "price_date",
            name="uq_market_price_day",
        ),
    )

    market_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("market_locations.id"), index=True, nullable=False
    )
    commodity: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    variety: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    grade: Mapped[str | None] = mapped_column(String(60))
    category: Mapped[str] = mapped_column(
        String(20), default=CommodityCategory.OTHER.value, nullable=False
    )

    minimum_price: Mapped[float] = mapped_column(Float, nullable=False)
    maximum_price: Mapped[float] = mapped_column(Float, nullable=False)
    modal_price: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(
        String(12), default=PriceUnit.QUINTAL.value, nullable=False
    )

    price_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class MarketPriceHistory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "market_price_history"
    __table_args__ = (
        UniqueConstraint(
            "market_id",
            "commodity",
            "variety",
            "recorded_date",
            name="uq_market_history_day",
        ),
    )

    market_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("market_locations.id"), index=True, nullable=False
    )
    commodity: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    variety: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    minimum_price: Mapped[float] = mapped_column(Float, nullable=False)
    maximum_price: Mapped[float] = mapped_column(Float, nullable=False)
    modal_price: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(
        String(12), default=PriceUnit.QUINTAL.value, nullable=False
    )
    recorded_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(40), nullable=False)


class MarketFavourite(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A farmer's saved market + commodity, for quick price checks."""

    __tablename__ = "market_favourites"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "commodity",
            "market_name",
            "district",
            name="uq_market_favourite",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    commodity: Mapped[str] = mapped_column(String(120), nullable=False)
    market_name: Mapped[str] = mapped_column(String(160), nullable=False)
    district: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str] = mapped_column(String(120), nullable=False)
