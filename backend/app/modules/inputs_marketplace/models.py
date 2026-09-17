from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from app.shared.base_model import GUID, Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship


class InputCatalogItem(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "input_catalog_items"
    __table_args__ = (
        CheckConstraint("unit_price > 0", name="ck_input_catalog_price_positive"),
        CheckConstraint("stock_quantity >= 0", name="ck_input_catalog_stock_nonnegative"),
        CheckConstraint("stock_version > 0", name="ck_input_catalog_version_positive"),
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    name_ta: Mapped[str | None] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stock_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    crop_tags: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)


class InputOrder(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "input_orders"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_input_order_user_idempotency"),
        CheckConstraint("total_amount > 0", name="ck_input_order_total_positive"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=False, index=True
    )
    order_ref: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="placed", index=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    delivery_address: Mapped[str] = mapped_column(String(500), nullable=False)
    delivery_eta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    cash_collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cash_collected_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("admin_users.id")
    )
    items: Mapped[list[InputOrderItem]] = relationship(
        back_populates="order", lazy="selectin", cascade="all, delete-orphan"
    )
    events: Mapped[list[InputOrderEvent]] = relationship(
        back_populates="order",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="InputOrderEvent.created_at",
    )


class InputOrderItem(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "input_order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_input_order_item_quantity_positive"),
        CheckConstraint("line_total > 0", name="ck_input_order_item_total_positive"),
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("input_orders.id"), nullable=False, index=True
    )
    catalog_item_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("input_catalog_items.id"), nullable=False, index=True
    )
    product_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    category_snapshot: Mapped[str] = mapped_column(String(24), nullable=False)
    unit_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    unit_price_snapshot: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    order: Mapped[InputOrder] = relationship(back_populates="items")


class InputOrderEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "input_order_events"
    order_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("input_orders.id"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    old_status: Mapped[str | None] = mapped_column(String(24))
    new_status: Mapped[str | None] = mapped_column(String(24))
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    actor_admin_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("admin_users.id"))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    note: Mapped[str | None] = mapped_column(String(500))
    order: Mapped[InputOrder] = relationship(back_populates="events")
