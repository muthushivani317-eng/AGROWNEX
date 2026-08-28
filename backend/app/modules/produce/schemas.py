"""Produce request/response schemas (docs/API_CONTRACT.md → PRODUCE)."""

from __future__ import annotations

import os
import uuid
from datetime import date, datetime
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.disease.constants import R2_PUBLIC_BASE_URL
from app.modules.produce.constants import (
    DEFAULT_CURRENCY,
    PRODUCE_TAXONOMY,
    ProduceAvailabilityType,
    ProduceCategory,
    ProduceGrade,
    ProduceStatus,
    ProduceUnit,
    QuantityProvenance,
    normalize_product_name,
    prohibited_product_term,
)
from app.modules.produce.engine import PriceReference, ProcurementInsight
from app.modules.produce.models import (
    ProduceOffer,
)


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #
class ProduceImageIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    image_url: str = Field(min_length=1, max_length=512)
    thumbnail_url: str | None = Field(default=None, max_length=512)
    mime_type: str | None = Field(default=None, max_length=80)
    file_size: int | None = Field(default=None, ge=0)
    caption: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_storage_image(self):
        environment = os.getenv("APP_ENV") or os.getenv("ENVIRONMENT") or "development"
        production = environment.lower() in {"production", "prod"}
        if production and not R2_PUBLIC_BASE_URL.startswith("https://"):
            raise ValueError("produce image storage is not configured")
        for field_name, value in (
            ("image_url", self.image_url),
            ("thumbnail_url", self.thumbnail_url),
        ):
            if value is None:
                continue
            parsed = urlsplit(value)
            if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
                raise ValueError(f"{field_name} must be an HTTPS object-storage URL")
            if R2_PUBLIC_BASE_URL and not value.startswith(f"{R2_PUBLIC_BASE_URL}/"):
                raise ValueError(f"{field_name} must use the configured object-storage origin")
        if self.mime_type not in {None, "image/jpeg", "image/png", "image/webp"}:
            raise ValueError("unsupported produce image MIME type")
        if self.file_size is not None and self.file_size > 8 * 1024 * 1024:
            raise ValueError("produce image exceeds 8 MB")
        return self


class ProduceOfferCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    farm_id: uuid.UUID
    crop_name: str | None = Field(default=None, min_length=1, max_length=80)
    product_name: str | None = Field(default=None, min_length=1, max_length=80)
    category: ProduceCategory = ProduceCategory.OTHER_PRODUCE
    availability_type: ProduceAvailabilityType = ProduceAvailabilityType.UPCOMING_HARVEST
    variety: str | None = Field(default=None, max_length=80)
    quantity: float = Field(gt=0, le=1_000_000)
    unit: ProduceUnit = ProduceUnit.QUINTAL
    cultivated_area_hectares: float | None = Field(default=None, gt=0, le=1_000_000)
    expected_total_quantity: float | None = Field(default=None, gt=0, le=1_000_000)
    available_quantity: float | None = Field(default=None, gt=0, le=1_000_000)
    quantity_provenance: Literal[QuantityProvenance.FARMER_REPORTED] | None = None
    quality_notes: str | None = Field(default=None, max_length=2000)
    expected_harvest_date: date | None = None
    expected_grade: ProduceGrade | None = None
    asking_price: float | None = Field(default=None, ge=0, le=10_000_000)
    packaging: str | None = Field(default=None, max_length=160)
    price_unit: str | None = Field(default=None, max_length=24)
    negotiable: bool = False
    pickup_available: bool = True
    pickup_location: str | None = Field(default=None, max_length=255)
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
    images: list[ProduceImageIn] = Field(default_factory=list, max_length=6)

    @model_validator(mode="after")
    def validate_quantities(self):
        name = (self.product_name or self.crop_name or "").strip()
        if not name:
            raise ValueError("product_name or crop_name is required")
        if prohibited_product_term(name):
            raise ValueError("Only agricultural produce can be listed")
        self.crop_name = name
        self.product_name = name
        canonical = PRODUCE_TAXONOMY.get(normalize_product_name(name))
        if canonical is not None:
            if "category" in self.model_fields_set and self.category.value != canonical:
                raise ValueError("category does not match the server produce taxonomy")
            self.category = ProduceCategory(canonical)
        elif self.category != ProduceCategory.OTHER_PRODUCE:
            raise ValueError("Unknown products must use other_produce for moderation")
        if canonical is None:
            self.status = ProduceStatus.DRAFT
        if (
            self.availability_type == ProduceAvailabilityType.UPCOMING_HARVEST
            and self.expected_harvest_date is None
        ):
            raise ValueError("expected_harvest_date is required for an upcoming harvest")
        if self.availability_type == ProduceAvailabilityType.AVAILABLE_NOW:
            self.expected_harvest_date = None
        if (
            self.available_quantity is not None
            and self.expected_total_quantity is not None
            and self.available_quantity > self.expected_total_quantity
        ):
            raise ValueError("available_quantity must not exceed expected_total_quantity")
        return self


class ProduceOfferUpdate(BaseModel):
    """Partial update — only provided fields change."""

    model_config = ConfigDict(extra="forbid")

    crop_name: str | None = Field(default=None, min_length=1, max_length=80)
    product_name: str | None = Field(default=None, min_length=1, max_length=80)
    category: ProduceCategory | None = None
    availability_type: ProduceAvailabilityType | None = None
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
    packaging: str | None = Field(default=None, max_length=160)
    price_unit: str | None = Field(default=None, max_length=24)
    negotiable: bool | None = None
    pickup_available: bool | None = None
    pickup_location: str | None = Field(default=None, max_length=255)
    available_from: date | None = None
    available_until: date | None = None
    district: str | None = Field(default=None, max_length=80)
    block: str | None = Field(default=None, max_length=80)
    village: str | None = Field(default=None, max_length=80)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    notes: str | None = Field(default=None, max_length=2000)
    status: ProduceStatus | None = None


class FarmerOfferDecisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["accepted", "rejected"]
    idempotency_key: str = Field(min_length=8, max_length=64)
    reason: str | None = Field(default=None, max_length=2000)


class FrozenBuyerOfferOut(BaseModel):
    offer_id: uuid.UUID
    case_id: uuid.UUID
    status: str
    terms_hash: str
    frozen_at: datetime
    terms: dict[str, Any]
    decision: str | None = None
    decided_at: datetime | None = None


class ProduceListFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: ProduceStatus | None = None
    crop: str | None = Field(default=None, max_length=80)
    farm_id: uuid.UUID | None = None
    category: ProduceCategory | None = None
    availability_type: ProduceAvailabilityType | None = None
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

    days_to_harvest: int | None
    harvest_window: str | None
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
    listing_ref: str
    farm_id: uuid.UUID
    crop_name: str
    product_name: str
    category: str
    availability_type: str
    variety: str | None
    quantity: float
    unit: str
    cultivated_area_hectares: float | None
    expected_total_quantity: float | None
    available_quantity: float | None
    quantity_provenance: str | None
    quality_notes: str | None
    expected_harvest_date: date | None
    expected_grade: str | None
    asking_price: float | None
    packaging: str | None
    price_unit: str | None
    negotiable: bool
    pickup_available: bool
    pickup_location: str | None
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
            listing_ref=offer.listing_ref,
            farm_id=offer.farm_id,
            crop_name=offer.crop_name,
            product_name=offer.crop_name,
            category=offer.product_category,
            availability_type=offer.availability_type,
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
            packaging=offer.packaging,
            price_unit=offer.price_unit,
            negotiable=offer.negotiable,
            pickup_available=offer.pickup_available,
            pickup_location=offer.pickup_location,
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
