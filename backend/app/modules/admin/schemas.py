"""Admin request/response schemas (docs: reuse response envelope; Tamil-first client).

Labels travel as data (localization codes handled by the client). Untracked metrics are
``None`` — surfaced honestly, never fabricated (docs/PRODUCT_RULES.md).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.admin.constants import ProcurementStatus
from app.modules.admin.engine import OverviewCard
from app.modules.admin.metrics import FarmerRow, ProcurementRow
from app.modules.admin.models import (
    AuditLog,
    BroadcastMessage,
    SystemAnnouncement,
)


# --------------------------------------------------------------------------- #
# Identity
# --------------------------------------------------------------------------- #
class AdminMeOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    role: str
    full_name: str | None
    permissions: list[str]
    status: str


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
class OverviewCardOut(BaseModel):
    key: str
    value: int | None

    @classmethod
    def from_card(cls, card: OverviewCard) -> OverviewCardOut:
        return cls(key=card.key, value=card.value)


class DashboardOut(BaseModel):
    cards: list[OverviewCardOut]
    procurement_status_counts: dict[str, int]
    generated_at: datetime


class CloudBillingSpendOut(BaseModel):
    project_id: str
    month: str
    budget_inr: float
    spend_inr: float | None
    remaining_inr: float | None
    percent_used: float | None
    status: Literal["available", "not_configured", "unavailable"]
    currency: str | None
    last_usage_at: datetime | None
    generated_at: datetime
    message: str | None = None


class RailwayBillingSpendOut(BaseModel):
    project_id: str
    spend_usd: float | None
    breakdown_usd: dict[str, float]
    status: Literal["available", "not_configured", "unavailable"]
    generated_at: datetime
    message: str | None = None


class ExpenseProviderOut(BaseModel):
    key: str
    label: str
    status: Literal["available", "not_configured", "unavailable"]
    amount: float | None
    currency: str
    amount_inr: float | None
    included_in_total: bool
    estimated: bool
    details: dict[str, float | int | str | None]
    message: str | None = None


class AllExpensesOut(BaseModel):
    month: str
    total_monthly_inr: float | None
    total_is_complete: bool
    usd_to_inr_rate: float | None
    providers: list[ExpenseProviderOut]
    generated_at: datetime
    message: str | None = None


# --------------------------------------------------------------------------- #
# Farmer management
# --------------------------------------------------------------------------- #
class FarmerRowOut(BaseModel):
    user_id: uuid.UUID
    farmer_ref: str
    full_name: str | None
    phone_number: str | None
    district: str | None
    village: str | None
    primary_crop: str | None
    language: str | None
    farm_count: int
    created_at: datetime | None

    @classmethod
    def from_row(cls, row: FarmerRow) -> FarmerRowOut:
        return cls(**row.__dict__)


class FarmSummaryOut(BaseModel):
    id: uuid.UUID
    name: str
    crop: str | None
    area_hectares: float | None
    status: str
    created_at: datetime


class FarmerDetailOut(BaseModel):
    user_id: uuid.UUID
    farmer_ref: str
    full_name: str | None
    phone_number: str | None
    district: str | None
    block: str | None
    village: str | None
    primary_crop: str | None
    language: str | None
    farms: list[FarmSummaryOut]
    counts: dict[str, int]
    consents: list[ConsentSummaryOut]

    @classmethod
    def from_detail(cls, user_id: uuid.UUID, detail: dict) -> FarmerDetailOut:
        profile = detail["profile"]
        user = detail["user"]
        return cls(
            user_id=user_id,
            farmer_ref=user.farmer_ref,
            full_name=getattr(profile, "full_name", None),
            phone_number=getattr(user, "phone_number", None),
            district=getattr(profile, "district", None),
            block=getattr(profile, "block", None),
            village=getattr(profile, "village", None),
            primary_crop=getattr(profile, "primary_crop", None),
            language=getattr(profile, "language", None),
            farms=[
                FarmSummaryOut(
                    id=f.id,
                    name=f.name,
                    crop=f.crop,
                    area_hectares=f.area_hectares,
                    status=f.status,
                    created_at=f.created_at,
                )
                for f in detail["farms"]
            ],
            counts=detail["counts"],
            consents=[ConsentSummaryOut(**item.__dict__) for item in detail["consents"]],
        )


class ConsentSummaryOut(BaseModel):
    purpose: str
    granted: bool
    version: int
    policy_version: str | None
    notice_hash: str | None
    channel: str | None
    locale: str | None
    decided_at: datetime | None


# --------------------------------------------------------------------------- #
# Analytics
# --------------------------------------------------------------------------- #
class DistributionItem(BaseModel):
    label: str
    count: int


class AnalyticsOut(BaseModel):
    farmer_growth: list[DistributionItem]
    crop_distribution: list[DistributionItem]
    disease_distribution: list[DistributionItem]
    nutrient_deficiencies: list[DistributionItem]
    soil_categories: list[DistributionItem]
    expert_trends: list[DistributionItem]
    produce_by_crop: list[DistributionItem]


class CropIntelligenceFiltersOut(BaseModel):
    crop: str | None
    district: str | None
    village: str | None
    harvest_days: int


class CropIntelligenceSummaryOut(BaseModel):
    farmer_count: int
    farm_count: int
    known_area_hectares: float
    farms_with_area: int
    farms_without_area: int
    recorded_stage_farms: int
    sale_listing_count: int
    harvest_window_farmer_count: int
    harvest_window_listing_count: int


class CropIntelligenceGroupOut(BaseModel):
    label: str
    farm_count: int
    farmer_count: int
    known_area_hectares: float
    farms_with_area: int


class CropStageCountOut(BaseModel):
    label: str
    farm_count: int


class OfferedQuantityOut(BaseModel):
    unit: str
    quantity: float


class HarvestWindowOut(BaseModel):
    from_date: date
    to_date: date
    farmer_count: int
    listing_count: int


class FarmIntelligenceRecordOut(BaseModel):
    farm_id: str
    name: str | None
    crop: str | None
    district: str | None
    area_hectares: float | None
    recorded_stage: str | None
    harvest_dates: list[date]


class CropIntelligenceOut(BaseModel):
    generated_at: datetime
    filters: CropIntelligenceFiltersOut
    summary: CropIntelligenceSummaryOut
    by_crop: list[CropIntelligenceGroupOut]
    by_location: list[CropIntelligenceGroupOut]
    crop_stages: list[CropStageCountOut]
    offered_quantities: list[OfferedQuantityOut]
    harvest_window: HarvestWindowOut
    farm_records: list[FarmIntelligenceRecordOut] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Procurement
# --------------------------------------------------------------------------- #
class ProcurementRowOut(BaseModel):
    offer_id: uuid.UUID
    listing_ref: str
    farmer_ref: str
    crop: str | None
    product_category: str
    availability_type: str
    variety: str | None
    quantity: float
    unit: str
    expected_grade: str | None
    harvest_date: datetime | None
    village: str | None
    district: str | None
    farmer_name: str | None
    offer_status: str
    admin_status: str
    assigned_admin_id: uuid.UUID | None = None
    follow_up_at: datetime | None = None
    buyer_name: str | None = None
    buyer_contact: str | None = None
    buyer_contact_masked: bool = False
    cultivated_area_hectares: float | None = None
    expected_total_quantity: float | None = None
    available_quantity: float | None = None
    quantity_provenance: str | None = None
    quality_notes: str | None = None
    buyer_offer_quantity: float | None = None
    buyer_offer_price: float | None = None
    transport_cost: float | None = None
    commission_rate: float | None = None
    negotiation_notes: str | None = None
    packaging: str | None = None
    asking_price: Decimal | None = None
    price_unit: str | None = None
    negotiable: bool = False
    pickup_available: bool = False
    pickup_location: str | None = None

    @classmethod
    def from_item(cls, item: dict) -> ProcurementRowOut:
        row: ProcurementRow = item["row"]
        case = item.get("case")
        return cls(
            offer_id=row.offer_id,
            listing_ref=row.listing_ref,
            farmer_ref=row.farmer_ref,
            crop=row.crop,
            product_category=row.product_category,
            availability_type=row.availability_type,
            variety=row.variety,
            quantity=row.quantity,
            unit=row.unit,
            expected_grade=row.expected_grade,
            harvest_date=row.harvest_date,
            village=row.village,
            district=row.district,
            farmer_name=row.farmer_name,
            offer_status=row.offer_status,
            admin_status=item["admin_status"],
            assigned_admin_id=getattr(case, "assigned_admin_id", None),
            follow_up_at=getattr(case, "follow_up_at", None),
            buyer_name=getattr(case, "buyer_name", None),
            buyer_contact=None,
            buyer_contact_masked=bool(getattr(case, "buyer_contact", None)),
            cultivated_area_hectares=row.cultivated_area_hectares,
            expected_total_quantity=row.expected_total_quantity,
            available_quantity=row.available_quantity,
            quantity_provenance=row.quantity_provenance,
            quality_notes=row.quality_notes,
            buyer_offer_quantity=getattr(case, "buyer_offer_quantity", None),
            buyer_offer_price=getattr(case, "buyer_offer_price", None),
            transport_cost=getattr(case, "transport_cost", None),
            commission_rate=getattr(case, "commission_rate", None),
            negotiation_notes=getattr(case, "negotiation_notes", None),
            packaging=row.packaging,
            asking_price=row.asking_price,
            price_unit=row.price_unit,
            negotiable=row.negotiable,
            pickup_available=row.pickup_available,
            pickup_location=row.pickup_location,
        )


class ProcurementBucket(BaseModel):
    label: str
    count: int
    quantity_kg: float


class QuantityTrendPoint(BaseModel):
    label: str
    quantity_kg: float
    count: int


class ProcurementAnalyticsOut(BaseModel):
    by_village: list[ProcurementBucket]
    by_crop: list[ProcurementBucket]
    by_season: list[ProcurementBucket]
    quantity_trend: list[QuantityTrendPoint]
    total_offers: int
    total_quantity_kg: float


# --------------------------------------------------------------------------- #
# AI monitoring
# --------------------------------------------------------------------------- #
class DailyPoint(BaseModel):
    label: str
    count: int


class AIMonitoringOut(BaseModel):
    today_requests: int | None
    total_messages: int | None
    disease_detections: int | None
    nutrient_analyses: int | None
    satellite_analyses: int | None
    memory_generated: int | None
    intelligence_reports: int | None
    average_confidence: int | None
    daily_requests: list[DailyPoint]
    model_latency_ms: int | None
    api_failures: int | None


class CostBucketOut(BaseModel):
    """One aggregation bucket for the AI cost dashboard (by model/module/date/week)."""

    key: str
    requests: int
    input_tokens: int
    output_tokens: int
    cost_inr: float


class AICostsOut(BaseModel):
    """Real AI spend aggregated per model and per module (Phase 1 cost control).

    Costs are estimated from the env-overridable INR cost table; requests with
    unknown token counts contribute 0 and are never fabricated.
    """

    window_days: int
    total_requests: int
    total_cost_inr: float
    by_model: list[CostBucketOut]
    by_module: list[CostBucketOut]
    daily: list[CostBucketOut]
    weekly: list[CostBucketOut]
    generated_at: datetime


# --------------------------------------------------------------------------- #
# Broadcast / notifications
# --------------------------------------------------------------------------- #
class BroadcastOut(BaseModel):
    id: uuid.UUID
    title: str
    body: str
    language: str
    target_type: str
    target_value: str | None
    schedule_type: str
    status: str
    recipient_count: int
    delivered_count: int
    scheduled_for: datetime | None
    sent_at: datetime | None
    created_at: datetime

    @classmethod
    def from_model(cls, b: BroadcastMessage) -> BroadcastOut:
        return cls(
            id=b.id,
            title=b.title,
            body=b.body,
            language=b.language,
            target_type=b.target_type,
            target_value=b.target_value,
            schedule_type=b.schedule_type,
            status=b.status,
            recipient_count=b.recipient_count,
            delivered_count=b.delivered_count,
            scheduled_for=b.scheduled_for,
            sent_at=b.sent_at,
            created_at=b.created_at,
        )


class BroadcastIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1)
    language: str = Field(default="ta", max_length=8)
    target_type: str = "all"
    target_value: str | None = None
    schedule_type: str = "immediate"
    scheduled_for: datetime | None = None


class AnnouncementOut(BaseModel):
    id: uuid.UUID
    title: str
    body: str
    language: str
    category: str | None
    audience: str
    is_active: bool
    starts_at: datetime | None
    ends_at: datetime | None
    created_at: datetime

    @classmethod
    def from_model(cls, a: SystemAnnouncement) -> AnnouncementOut:
        return cls(
            id=a.id,
            title=a.title,
            body=a.body,
            language=a.language,
            category=a.category,
            audience=a.audience,
            is_active=a.is_active,
            starts_at=a.starts_at,
            ends_at=a.ends_at,
            created_at=a.created_at,
        )


class AnnouncementIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1)
    language: str = Field(default="ta", max_length=8)
    category: str | None = None
    audience: str = "all"


class ProcurementStatusIn(BaseModel):
    status: str
    note: str | None = None


class ProcurementCaseUpdateIn(BaseModel):
    status: ProcurementStatus | None = None
    assigned_admin_id: uuid.UUID | None = None
    follow_up_at: datetime | None = None
    buyer_name: str | None = Field(default=None, max_length=160)
    buyer_contact: str | None = Field(default=None, max_length=160)
    buyer_offer_quantity: float | None = Field(default=None, gt=0, le=1_000_000)
    buyer_offer_price: Decimal | None = Field(
        default=None, gt=0, le=10_000_000, max_digits=14, decimal_places=2
    )
    transport_cost: Decimal | None = Field(
        default=None, ge=0, le=10_000_000, max_digits=14, decimal_places=2
    )
    commission_rate: Decimal | None = Field(
        default=None, ge=0, le=100, max_digits=5, decimal_places=2
    )
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    price_unit: str | None = Field(default=None, min_length=1, max_length=16)
    negotiation_notes: str | None = Field(default=None, max_length=4000)


class PickupLedgerIn(BaseModel):
    status: Literal["scheduled", "completed", "failed", "cancelled"]
    scheduled_at: datetime | None = None
    occurred_at: datetime | None = None
    location: str | None = Field(default=None, max_length=255)
    note: str | None = Field(default=None, max_length=2000)


class TransactionIn(BaseModel):
    occurred_at: datetime


class PaymentLedgerIn(BaseModel):
    entry_type: Literal["buyer_receipt", "farmer_payout", "refund"]
    amount: Decimal = Field(gt=0, le=100_000_000, max_digits=14, decimal_places=2)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    reference: str | None = Field(default=None, max_length=160)
    occurred_at: datetime


class CommissionLedgerIn(BaseModel):
    entry_type: Literal["earned", "reversed", "paid"] = "earned"
    occurred_at: datetime


# --------------------------------------------------------------------------- #
# Audit
# --------------------------------------------------------------------------- #
class AuditRowOut(BaseModel):
    id: uuid.UUID
    admin_id: uuid.UUID | None
    role: str | None
    action: str
    target: str | None
    target_id: str | None
    ip_address: str | None
    meta: dict | None
    created_at: datetime

    @classmethod
    def from_model(cls, a: AuditLog) -> AuditRowOut:
        return cls(
            id=a.id,
            admin_id=a.admin_id,
            role=a.role,
            action=a.action,
            target=a.target,
            target_id=a.target_id,
            ip_address=a.ip_address,
            meta=a.meta,
            created_at=a.created_at,
        )


__all__ = [
    "AdminMeOut",
    "AnalyticsOut",
    "AnnouncementIn",
    "AnnouncementOut",
    "AIMonitoringOut",
    "AuditRowOut",
    "BroadcastIn",
    "BroadcastOut",
    "DashboardOut",
    "DistributionItem",
    "FarmerDetailOut",
    "FarmerRowOut",
    "OverviewCardOut",
    "ProcurementAnalyticsOut",
    "ProcurementRowOut",
    "ProcurementStatusIn",
    "date",
]
