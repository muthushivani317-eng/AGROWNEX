from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from app.modules.inputs_marketplace.constants import InputCategory, InputOrderStatus
from pydantic import BaseModel, Field


class CatalogItemOut(BaseModel):
    id: uuid.UUID
    name: str
    name_ta: str | None
    category: str
    unit: str
    unit_price: Decimal
    stock_quantity: int
    stock_version: int
    crop_tags: list[str]
    description: str | None
    is_active: bool
    updated_at: datetime


class CatalogItemWrite(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    name_ta: str | None = Field(default=None, max_length=160)
    category: InputCategory
    unit: str = Field(min_length=1, max_length=32)
    unit_price: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    stock_quantity: int = Field(ge=0, le=1_000_000)
    crop_tags: list[str] = Field(default_factory=list, max_length=30)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool = True


class CartLineIn(BaseModel):
    catalog_item_id: uuid.UUID
    quantity: int = Field(ge=1, le=10_000)
    expected_unit_price: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    expected_stock_version: int = Field(ge=1)


class PlaceOrderIn(BaseModel):
    items: list[CartLineIn] = Field(min_length=1, max_length=50)
    delivery_address: str = Field(min_length=10, max_length=500)
    idempotency_key: str = Field(min_length=16, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")


class OrderItemOut(BaseModel):
    product_name: str
    category: str
    unit: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal


class OrderEventOut(BaseModel):
    event_type: str
    old_status: str | None
    new_status: str | None
    amount: Decimal | None
    created_at: datetime


class OrderOut(BaseModel):
    id: uuid.UUID
    order_ref: str
    status: str
    total_amount: Decimal
    currency: str
    delivery_address: str
    delivery_eta: datetime | None
    cash_collected_at: datetime | None
    created_at: datetime
    items: list[OrderItemOut]
    events: list[OrderEventOut]


class AdminOrderUpdate(BaseModel):
    status: InputOrderStatus
    delivery_eta: datetime | None = None
    note: str | None = Field(default=None, max_length=500)


class CashSummaryOut(BaseModel):
    delivered_orders: int
    cash_collected_total: Decimal
    currency: str = "INR"
