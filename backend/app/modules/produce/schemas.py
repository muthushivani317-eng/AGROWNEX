"""Produce request/response schemas (docs/API_CONTRACT.md → PRODUCE)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.produce.constants import (
    DEFAULT_CURRENCY,
    ProduceGrade,
    ProduceStatus,
    ProduceUnit,
    QuantityProvenance,
)
from app.modules.produce.engine import PriceReference, ProcurementInsight
from app.modules.produce.models import (
    ProduceOffer,
)


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #
class ProduceImageIn(BaseModel):
    image_url: str = Field(min_length=1, max_length=512)
    thumbnail_url: str | None = Field(default=None, max_length=512)
    mime_type: str | None = Field(default=None, max_length=80)
    file_size: int | None = Field(default=None, ge=0)
    caption: str | None = Field(default=None, max_length=255)


class ProduceOfferCreate(BaseModel):
    farm_id: uuid.UUID
    crop_name: str = Field(min_length=1, max_length=80)
    variety: str | None = Field(default=None, max_length=80)
    quantity: float = Field(gt=0, le=1_000_000)
    unit: ProduceUnit = ProduceUnit.QUINTAL
    cultivated_area_hectares: float | None = Field(default=None, gt=0, le=1_000_000)
    expected_total_quantity: float | None = Field(default=None, gt=0, le=1_000_000)
    available_quantity: float | None = Field(default=None, gt=0, le=1_000_000)
    quantity_provenance: Literal[QuantityProvenance.FARMER_REPORTED] | None = None
    quality_notes: str | None = Field(default=None, max_length=2000)
    expected_harvest_date: date
    expected_grade: ProduceGrade | None = None
    asking_price: float | None = Field(default=None, ge=0, le=10_000_000)
    currency: str = Field(default=DEFAULT_CURRENCY, min_length=3, max_length=3)
    available_from: date | None = None
    available_until: date | None = None
    district: str | None = Field(default=None, max_length=80)
    block: str | None = Field(default=None, max_length=80)
    village: str | None = Field(default=None, max_length=80)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    notes: str | None = Field(default=None, max_length=2000)
    status: ProduceStatus = ProduceStatus.SUBMITTED
    images: list[ProduceImageIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_quantities(self):
        if (
            self.available_quantity is not None
            and self.expected_total_quantity is not None
            and self.available_quantity > self.expected_total_quantity
        ):
            raise ValueError("available_quantity must not exceed expected_total_quantity")
        return self


class ProduceOfferUpdate(BaseModel):
    """Partial update — only provided fields change."""

    crop_name: str | None = Field(default=None, min_length=1, max_length=80)
    variety: str | None = Field(default=None, max_length=80)
    quantity: float | None = Field(default=None, gt=0, le=1_000_000)
    unit: ProduceUnit | None = None
    cultivated_area_hectares: float | None = Field(default=None, gt=0, le=1_000_000)
    expected_total_quantity: float | None = Field(default=None, gt=0, le=1_000_000)
    available_quantity: float | None = Field(default=None, gt=0, le=1_000_000)
    quantity_provenance: Literal[QuantityProvenance.FARMER_REPORTED] | None = None
    quality_notes: str | None = Field(default=None, max_length=2000)
    expected_harvest_date: date | None = None
    expected_grade: ProduceGrade | None = None
    asking_price: float | None = Field(default=None, ge=0, le=10_000_000)
    available_from: date | None = None
    available_until: date | None = None
    district: str | None = Field(default=None, max_length=80)
    block: str | None = Field(default=None, max_length=80)
    village: str | None = Field(default=None, max_length=80)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    notes: str | None = Field(default=None, max_length=2000)
    status: ProduceStatus | None = None


class ProduceListFilters(BaseModel):
    status: ProduceStatus | None = None
    crop: str | None = Field(default=None, max_length=80)
    farm_id: uuid.UUID | None = None
    search: str | None = Field(default=None, max_length=120)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# --------------------------------------------------------------------------- #
# Outputs
# --------------------------------------------------------------------------- #
class ProduceImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    image_url: str
    thumbnail_url: str | None
    mime_type: str | None
    caption: str | None
    display_order: int
    created_at: datetime


class StatusHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    old_status: str | None
    new_status: str
    note: str | None
    created_at: datetime


class PriceReferenceOut(BaseModel):
    modal_price: float
    minimum_price: float
    maximum_price: float
    unit: str
    source: str
    price_date: date
    market: str | None = None
    district: str | None = None

    @classmethod
    def from_reference(cls, ref: PriceReference) -> PriceReferenceOut:
        return cls(
            modal_price=ref.modal_price,
            minimum_price=ref.minimum_price,
            maximum_price=ref.maximum_price,
            unit=ref.unit,
            source=ref.source,
            price_date=ref.price_date,
            market=ref.market,
            district=ref.district,
        )


class ProcurementInsightOut(BaseModel):
    """The deterministic engine's output for a single offer."""

    days_to_harvest: int
    harvest_window: str
    quantity_kg: float | None
    estimated_market_value: float | None
    estimated_asking_value: float | None
    price_reference: PriceReferenceOut | None

    @classmethod
    def from_insight(cls, insight: ProcurementInsight) -> ProcurementInsightOut:
        return cls(
            days_to_harvest=insight.days_to_harvest,
            harvest_window=insight.harvest_window,
            quantity_kg=insight.quantity_kg,
            estimated_market_value=insight.estimated_market_value,
            estimated_asking_value=insight.estimated_asking_value,
            price_reference=(
                PriceReferenceOut.from_reference(insight.price_reference)
                if insight.price_reference
                else None
            ),
        )


class ProduceOfferSummaryOut(BaseModel):
    id: uuid.UUID
    farm_id: uuid.UUID
    crop_name: str
    variety: str | None
    quantity: float
    unit: str
    cultivated_area_hectares: float | None
    expected_total_quantity: float | None
    available_quantity: float | None
    quantity_provenance: str | None
    quality_notes: str | None
    expected_harvest_date: date
    expected_grade: str | None
    asking_price: float | None
    currency: str
    current_market_price_snapshot: float | None
    district: str | None
    status: str
    thumbnail_url: str | None
    image_count: int
    insight: ProcurementInsightOut | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_offer(
        cls,
        offer: ProduceOffer,
        *,
        insight: ProcurementInsight | None = None,
    ) -> ProduceOfferSummaryOut:
        images = offer.images or []
        return cls(
            id=offer.id,
            farm_id=offer.farm_id,
            crop_name=offer.crop_name,
            variety=offer.variety,
            quantity=offer.quantity,
            unit=offer.unit,
            cultivated_area_hectares=offer.cultivated_area_hectares,
            expected_total_quantity=offer.expected_total_quantity,
            available_quantity=offer.available_quantity,
            quantity_provenance=offer.quantity_provenance,
            quality_notes=offer.quality_notes,
            expected_harvest_date=offer.expected_harvest_date,
            expected_grade=offer.expected_grade,
            asking_price=offer.asking_price,
            currency=offer.currency,
            current_market_price_snapshot=offer.current_market_price_snapshot,
            district=offer.district,
            status=offer.status,
            thumbnail_url=(images[0].thumbnail_url or images[0].image_url) if images else None,
            image_count=len(images),
            insight=(ProcurementInsightOut.from_insight(insight) if insight else None),
            created_at=offer.created_at,
            updated_at=offer.updated_at,
        )


class ProduceOfferDetailOut(ProduceOfferSummaryOut):
    block: str | None
    village: str | None
    latitude: float | None
    longitude: float | None
    available_from: date | None
    available_until: date | None
    market_price_source: str | None
    market_price_date: date | None
    procurement_channel: str | None
    procurement_reference: str | None
    notes: str | None
    images: list[ProduceImageOut]
    status_history: list[StatusHistoryOut]

    @classmethod
    def from_offer_detail(
        cls,
        offer: ProduceOffer,
        *,
        insight: ProcurementInsight | None = None,
    ) -> ProduceOfferDetailOut:
        base = ProduceOfferSummaryOut.from_offer(offer, insight=insight)
        return cls(
            **base.model_dump(),
            block=offer.block,
            village=offer.village,
            latitude=offer.latitude,
            longitude=offer.longitude,
            available_from=offer.available_from,
            available_until=offer.available_until,
            market_price_source=offer.market_price_source,
            market_price_date=offer.market_price_date,
            procurement_channel=offer.procurement_channel,
            procurement_reference=offer.procurement_reference,
            notes=offer.notes,
            images=[ProduceImageOut.model_validate(i) for i in (offer.images or [])],
            status_history=[
                StatusHistoryOut.model_validate(h) for h in (offer.status_history or [])
            ],
        )
