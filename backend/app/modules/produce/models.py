"""Produce ORM models (docs/DATABASE_SCHEMA.md → Produce domain).

Normalized tables:

* ``produce_offers``        — one verified future-harvest offer per row (farmer +
  farm scoped). Carries the harvest facts, a nullable *verified* market-price
  snapshot, and reserved future-ready columns so buyer matching / auctions /
  procurement AI / demand prediction / warehouse / cold storage / transport /
  export readiness need **no schema redesign**.
* ``offer_images``          — uploaded harvest photos (S3/R2 URL + metadata).
* ``offer_status_history``  — the procurement lifecycle trail.
* ``buyer_interest``        — future-ready: expressions of interest from a
  procurement channel. Unused in V1 (no fabricated buyers), reserved so future
  buyer integration requires no schema redesign.

``user_id`` is the farmer (FK ``users.id``) — the codebase scopes every module by
the authenticated user, matching the docs' ``farmer_id`` concept.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.produce.constants import (
    DEFAULT_CURRENCY,
    ProduceStatus,
)
from app.shared.base_model import (
    GUID,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)


class ProduceOffer(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "produce_offers"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True, nullable=False
    )
    # Reserved link to a growth/crop session (future timeline joins); nullable.
    crop_session_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), index=True)

    crop_name: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    variety: Mapped[str | None] = mapped_column(String(80))
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(12), nullable=False)
    expected_harvest_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    expected_grade: Mapped[str | None] = mapped_column(String(12))

    asking_price: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default=DEFAULT_CURRENCY, nullable=False)

    # Verified market-price snapshot at capture (nullable — never fabricated).
    # Frozen at write time so reads never re-query and the snapshot stays faithful.
    current_market_price_snapshot: Mapped[float | None] = mapped_column(Float)
    market_price_min: Mapped[float | None] = mapped_column(Float)
    market_price_max: Mapped[float | None] = mapped_column(Float)
    market_price_unit: Mapped[str | None] = mapped_column(String(12))
    market_price_source: Mapped[str | None] = mapped_column(String(40))
    market_price_date: Mapped[date | None] = mapped_column(Date)

    # Harvest availability window (docs: available_from / available_until).
    available_from: Mapped[date | None] = mapped_column(Date)
    available_until: Mapped[date | None] = mapped_column(Date)

    # Location — defaults resolved from the farm, overridable per offer.
    district: Mapped[str | None] = mapped_column(String(80), index=True)
    block: Mapped[str | None] = mapped_column(String(80))
    village: Mapped[str | None] = mapped_column(String(80))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(12), default=ProduceStatus.SUBMITTED.value, nullable=False, index=True
    )

    # Procurement channel routing (docs: eNAM / FPO / private / export / admin).
    procurement_channel: Mapped[str | None] = mapped_column(String(20))
    procurement_reference: Mapped[str | None] = mapped_column(String(80))

    # Future-ready payloads — populated by later features, no schema redesign:
    ai_grade: Mapped[dict | None] = mapped_column(JSON)  # AI quality grading
    buyer_match: Mapped[dict | None] = mapped_column(JSON)  # buyer matching / auction
    logistics: Mapped[dict | None] = mapped_column(JSON)  # transport/warehouse/cold/export

    images: Mapped[list[OfferImage]] = relationship(
        back_populates="offer",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="OfferImage.display_order",
    )
    status_history: Mapped[list[OfferStatusHistory]] = relationship(
        back_populates="offer",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="OfferStatusHistory.created_at",
    )


class OfferImage(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "offer_images"

    offer_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("produce_offers.id"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    image_url: Mapped[str] = mapped_column(String(512), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(512))
    mime_type: Mapped[str | None] = mapped_column(String(80))
    file_size: Mapped[int | None] = mapped_column(Integer)
    caption: Mapped[str | None] = mapped_column(String(255))
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    offer: Mapped[ProduceOffer] = relationship(back_populates="images")


class OfferStatusHistory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "offer_status_history"

    offer_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("produce_offers.id"), index=True, nullable=False
    )
    old_status: Mapped[str | None] = mapped_column(String(12))
    new_status: Mapped[str] = mapped_column(String(12), nullable=False)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    note: Mapped[str | None] = mapped_column(String(255))

    offer: Mapped[ProduceOffer] = relationship(back_populates="status_history")


class BuyerInterest(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Future-ready: interest from a procurement channel. Unused in V1."""

    __tablename__ = "buyer_interest"

    offer_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("produce_offers.id"), index=True, nullable=False
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    buyer_name: Mapped[str | None] = mapped_column(String(160))
    buyer_type: Mapped[str | None] = mapped_column(String(20))
    contact: Mapped[str | None] = mapped_column(String(120))
    offered_price: Mapped[float | None] = mapped_column(Float)
    quantity: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    external_reference: Mapped[str | None] = mapped_column(String(80))


class HarvestReadinessRecord(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "harvest_readiness_records"

    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), index=True)
    farm_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("farms.id"), index=True)
    crop_cycle_id: Mapped[str] = mapped_column(String(80), index=True)
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    criteria_version: Mapped[str | None] = mapped_column(String(80))
    criteria_hash: Mapped[str | None] = mapped_column(String(64))
    evidence_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    pending_sync: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class HarvestReadinessHistory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "harvest_readiness_history"

    record_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("harvest_readiness_records.id"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), index=True)
    event: Mapped[str] = mapped_column(String(24), nullable=False)
    prior_state: Mapped[str | None] = mapped_column(String(40))
    next_state: Mapped[str] = mapped_column(String(40), nullable=False)
    note: Mapped[str | None] = mapped_column(String(500))
    photo_reference: Mapped[str | None] = mapped_column(String(512))
    idempotency_key: Mapped[str] = mapped_column(String(100), index=True)
    evidence_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    farmer_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ProduceTraceBatch(UUIDMixin, TimestampMixin, Base):
    """Controlled-test traceability identity for one farmer-owned produce offer."""

    __tablename__ = "produce_trace_batches"

    offer_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("produce_offers.id", ondelete="CASCADE"), unique=True, index=True
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    batch_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)


class ProduceTraceEvent(UUIDMixin, TimestampMixin, Base):
    """Append-only, hash-chained farmer declaration; not a certification record."""

    __tablename__ = "produce_trace_events"

    batch_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("produce_trace_batches.id", ondelete="CASCADE"), index=True
    )
    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    location_text: Mapped[str | None] = mapped_column(String(160))
    notes: Mapped[str | None] = mapped_column(String(1000))
    evidence_url: Mapped[str | None] = mapped_column(String(512))
    previous_hash: Mapped[str | None] = mapped_column(String(64))
    event_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
