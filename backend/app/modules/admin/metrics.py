"""Admin metrics — read-only aggregation over every module (docs: dashboard/analytics).

The I/O boundary between the Admin Engine and the rest of AgrowAI. Every query is
read-only (docs: no direct farmer data modification) and guarded, so one module failing
never breaks the dashboard. Counts and group-bys are real — nothing is fabricated
(docs/PRODUCT_RULES.md → uncertainty is surfaced, e.g. untracked metrics stay ``None``).
"""

from __future__ import annotations

import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.admin.constants import ACTIVE_USER_DAYS

logger = get_logger("admin.metrics")


@dataclass
class FarmerRow:
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


@dataclass
class ProcurementRow:
    offer_id: uuid.UUID
    listing_ref: str
    farmer_ref: str
    user_id: uuid.UUID
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
    farmer_phone: str | None
    offer_status: str
    cultivated_area_hectares: float | None
    expected_total_quantity: float | None
    available_quantity: float | None
    quantity_provenance: str | None
    quality_notes: str | None
    packaging: str | None
    asking_price: Decimal | None
    price_unit: str | None
    negotiable: bool
    pickup_available: bool
    pickup_location: str | None
    organic_certification_status: str | None = None
    organic_certification_verified: bool = False


@dataclass
class Distribution:
    key: str
    items: list[dict] = field(default_factory=list)


class AdminMetrics:
    def __init__(self, session: AsyncSession, *, now: datetime | None = None) -> None:
        self.session = session
        self.now = now or datetime.now(UTC)

    async def _count(self, name: str, stmt) -> int | None:  # noqa: ANN001
        try:
            res = await self.session.execute(select(func.count()).select_from(stmt.subquery()))
            return int(res.scalar_one())
        except Exception:  # noqa: BLE001 — one module must never break the dashboard
            logger.exception("admin metric '%s' failed; reporting null", name)
            return None

    # ----------------------------------------------------------------- #
    # Overview cards
    # ----------------------------------------------------------------- #
    async def overview(self) -> dict[str, int | None]:
        from app.modules.ai.models import AIConversation
        from app.modules.auth.models import User
        from app.modules.auth.profile_models import FarmerProfile
        from app.modules.disease.models import DiseaseReport
        from app.modules.experts.models import Consultation
        from app.modules.farms.models import Farm
        from app.modules.intelligence.models import CropIntelligenceReport
        from app.modules.notifications.models import Notification
        from app.modules.produce.models import ProduceOffer
        from app.modules.satellite.models import SatelliteSession
        from app.modules.schemes.models import SchemeBookmark
        from app.modules.soil.models import SoilReport

        day_start = self.now.replace(hour=0, minute=0, second=0, microsecond=0)
        active_since = self.now - timedelta(days=ACTIVE_USER_DAYS)

        return {
            "total_farmers": await self._count(
                "total_farmers",
                select(FarmerProfile).where(FarmerProfile.is_deleted.is_(False)),
            ),
            "total_farms": await self._count(
                "total_farms", select(Farm).where(Farm.is_deleted.is_(False))
            ),
            "active_users": await self._count(
                "active_users", select(User).where(User.last_login >= active_since)
            ),
            "today_ai_chats": await self._count(
                "today_ai_chats",
                select(AIConversation).where(AIConversation.created_at >= day_start),
            ),
            "disease_reports": await self._count("disease_reports", select(DiseaseReport)),
            "soil_reports": await self._count(
                "soil_reports", select(SoilReport).where(SoilReport.is_deleted.is_(False))
            ),
            "satellite_reports": await self._count(
                "satellite_reports",
                select(SatelliteSession).where(SatelliteSession.is_deleted.is_(False)),
            ),
            "intelligence_reports": await self._count(
                "intelligence_reports",
                select(CropIntelligenceReport).where(CropIntelligenceReport.is_deleted.is_(False)),
            ),
            "scheme_saves": await self._count(
                "scheme_saves",
                select(SchemeBookmark).where(SchemeBookmark.is_deleted.is_(False)),
            ),
            "produce_listings": await self._count(
                "produce_listings",
                select(ProduceOffer).where(ProduceOffer.is_deleted.is_(False)),
            ),
            "expert_consultations": await self._count(
                "expert_consultations",
                select(Consultation).where(Consultation.is_deleted.is_(False)),
            ),
            "notifications_sent": await self._count("notifications_sent", select(Notification)),
        }

    # ----------------------------------------------------------------- #
    # AI monitoring
    # ----------------------------------------------------------------- #
    async def ai_monitoring(self) -> dict:
        from app.modules.ai.models import AIConversation, AIMessage
        from app.modules.disease.models import DiseaseReport
        from app.modules.intelligence.models import CropIntelligenceReport
        from app.modules.memory.models import FarmMemory
        from app.modules.nutrient.models import NutrientReport
        from app.modules.satellite.models import SatelliteSession

        day_start = self.now.replace(hour=0, minute=0, second=0, microsecond=0)

        avg_conf = await self._avg_confidence()
        daily = await self._daily_ai_series(days=7)

        return {
            "today_requests": await self._count(
                "ai_today",
                select(AIConversation).where(AIConversation.created_at >= day_start),
            ),
            "total_messages": await self._count("ai_messages", select(AIMessage)),
            "disease_detections": await self._count("ai_disease", select(DiseaseReport)),
            "nutrient_analyses": await self._count("ai_nutrient", select(NutrientReport)),
            "satellite_analyses": await self._count(
                "ai_satellite",
                select(SatelliteSession).where(SatelliteSession.status == "available"),
            ),
            "memory_generated": await self._count(
                "ai_memory", select(FarmMemory).where(FarmMemory.is_deleted.is_(False))
            ),
            "intelligence_reports": await self._count(
                "ai_intel",
                select(CropIntelligenceReport).where(CropIntelligenceReport.is_deleted.is_(False)),
            ),
            "average_confidence": avg_conf,
            "daily_requests": daily,
            # Not instrumented in V1 — surfaced honestly as unavailable, never faked.
            "model_latency_ms": None,
            "api_failures": None,
        }

    async def _avg_confidence(self) -> int | None:
        from app.modules.disease.models import DiseaseReport
        from app.modules.nutrient.models import NutrientAnalysis, NutrientReport
        from app.modules.nutrient.safety import consumer_safe_nutrient_finding

        try:
            d = (
                await self.session.execute(
                    select(func.avg(DiseaseReport.confidence)).where(
                        DiseaseReport.confidence.is_not(None)
                    )
                )
            ).scalar_one_or_none()
            nutrient_rows = (
                await self.session.execute(
                    select(
                        NutrientAnalysis.confidence,
                        NutrientAnalysis.primary_deficiency,
                        NutrientAnalysis.status,
                        NutrientAnalysis.needs_test,
                        NutrientAnalysis.needs_expert,
                        NutrientReport.crop,
                    ).join(NutrientReport, NutrientReport.id == NutrientAnalysis.report_id)
                )
            ).all()
            safe_confidences = [
                safe.confidence
                for confidence, primary, status, needs_test, needs_expert, crop in nutrient_rows
                if (
                    safe := consumer_safe_nutrient_finding(
                        crop=crop,
                        primary_deficiency=primary,
                        status=status,
                        confidence=confidence,
                        needs_test=bool(needs_test),
                        needs_expert=bool(needs_expert),
                    )
                ).confidence is not None
            ]
            n = sum(safe_confidences) / len(safe_confidences) if safe_confidences else None
            vals = [v for v in (d, n) if v is not None]
            return round(sum(vals) / len(vals)) if vals else None
        except Exception:  # noqa: BLE001
            logger.exception("admin avg confidence failed")
            return None

    async def _nutrient_distribution(self) -> list[dict]:
        from app.modules.nutrient.models import NutrientAnalysis, NutrientReport
        from app.modules.nutrient.safety import consumer_safe_nutrient_finding

        try:
            rows = (
                await self.session.execute(
                    select(
                        NutrientAnalysis.primary_deficiency,
                        NutrientAnalysis.status,
                        NutrientAnalysis.confidence,
                        NutrientAnalysis.needs_test,
                        NutrientAnalysis.needs_expert,
                        NutrientReport.crop,
                    ).join(NutrientReport, NutrientReport.id == NutrientAnalysis.report_id)
                )
            ).all()
            counts = Counter()
            for primary, status, confidence, needs_test, needs_expert, crop in rows:
                safe = consumer_safe_nutrient_finding(
                    crop=crop,
                    primary_deficiency=primary,
                    status=status,
                    confidence=confidence,
                    needs_test=bool(needs_test),
                    needs_expert=bool(needs_expert),
                )
                if primary and not safe.groundnut_specific_restricted:
                    counts[primary] += 1
            return [
                {"label": label, "count": count}
                for label, count in counts.most_common()
            ]
        except Exception:  # noqa: BLE001
            logger.exception("admin nutrient distribution failed")
            return []

    async def _daily_ai_series(self, *, days: int) -> list[dict]:
        from app.modules.ai.models import AIConversation

        out: list[dict] = []
        try:
            for i in range(days - 1, -1, -1):
                start = (self.now - timedelta(days=i)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                end = start + timedelta(days=1)
                count = int(
                    (
                        await self.session.execute(
                            select(func.count())
                            .select_from(AIConversation)
                            .where(
                                AIConversation.created_at >= start,
                                AIConversation.created_at < end,
                            )
                        )
                    ).scalar_one()
                )
                out.append({"label": start.strftime("%Y-%m-%d"), "count": count})
        except Exception:  # noqa: BLE001
            logger.exception("admin daily AI series failed")
        return out

    # ----------------------------------------------------------------- #
    # Analytics distributions
    # ----------------------------------------------------------------- #
    async def _group(self, name: str, column, stmt) -> list[dict]:  # noqa: ANN001
        try:
            rows = (
                await self.session.execute(stmt.group_by(column).order_by(func.count().desc()))
            ).all()
            return [{"label": (label or "unknown"), "count": int(count)} for label, count in rows]
        except Exception:  # noqa: BLE001
            logger.exception("admin distribution '%s' failed", name)
            return []

    async def analytics(self) -> dict:
        from app.modules.disease.models import DiseaseReport
        from app.modules.experts.models import Consultation
        from app.modules.farms.models import Farm
        from app.modules.produce.models import ProduceOffer

        crop_distribution = await self._group(
            "crop", Farm.crop, select(Farm.crop, func.count()).where(Farm.is_deleted.is_(False))
        )
        disease_distribution = await self._group(
            "disease",
            DiseaseReport.disease,
            select(DiseaseReport.disease, func.count()).where(DiseaseReport.disease.is_not(None)),
        )
        nutrient_deficiencies = await self._nutrient_distribution()
        soil_categories = await self._group(
            "soil",
            Farm.soil_type,
            select(Farm.soil_type, func.count()).where(Farm.is_deleted.is_(False)),
        )
        expert_trends = await self._group(
            "experts",
            Consultation.status,
            select(Consultation.status, func.count()).where(Consultation.is_deleted.is_(False)),
        )
        produce_by_crop = await self._group(
            "produce",
            ProduceOffer.crop_name,
            select(ProduceOffer.crop_name, func.count()).where(ProduceOffer.is_deleted.is_(False)),
        )
        farmer_growth = await self._farmer_growth(months=6)

        return {
            "farmer_growth": farmer_growth,
            "crop_distribution": crop_distribution,
            "disease_distribution": disease_distribution,
            "nutrient_deficiencies": nutrient_deficiencies,
            "soil_categories": soil_categories,
            "expert_trends": expert_trends,
            "produce_by_crop": produce_by_crop,
        }

    async def crop_intelligence(
        self,
        *,
        crop: str | None = None,
        district: str | None = None,
        village: str | None = None,
        harvest_days: int = 30,
    ) -> dict:
        """Live, recorded crop supply facts for commercial planning.

        Acreage is summed only where a farmer supplied it. Harvest-window counts
        require a dated submitted/planned produce offer; no crop calendar estimate
        is presented as farmer inventory.
        """
        from app.modules.farms.models import Farm, FarmLocation
        from app.modules.growth.models import CropGrowthSession, CropStageState
        from app.modules.produce.constants import ProduceStatus
        from app.modules.produce.models import ProduceOffer

        filters = [Farm.is_deleted.is_(False)]
        if crop:
            filters.append(func.lower(Farm.crop) == crop.strip().lower())
        if district:
            filters.append(func.lower(FarmLocation.district) == district.strip().lower())
        if village:
            filters.append(func.lower(FarmLocation.village) == village.strip().lower())

        farm_rows = (
            await self.session.execute(
                select(Farm, FarmLocation)
                .outerjoin(FarmLocation, FarmLocation.farm_id == Farm.id)
                .where(*filters)
            )
        ).all()
        farms = [row[0] for row in farm_rows]
        locations = {row[0].id: row[1] for row in farm_rows}
        farm_ids = [farm.id for farm in farms]

        def group_rows(key_fn) -> list[dict]:  # noqa: ANN001
            grouped: dict[str, dict] = {}
            for farm in farms:
                key = key_fn(farm) or "Unknown"
                item = grouped.setdefault(
                    key,
                    {
                        "label": key,
                        "farm_ids": set(),
                        "farmer_ids": set(),
                        "known_area_hectares": 0.0,
                        "farms_with_area": 0,
                    },
                )
                item["farm_ids"].add(farm.id)
                item["farmer_ids"].add(farm.user_id)
                if farm.area_hectares is not None:
                    item["known_area_hectares"] += float(farm.area_hectares)
                    item["farms_with_area"] += 1
            return [
                {
                    "label": item["label"],
                    "farm_count": len(item["farm_ids"]),
                    "farmer_count": len(item["farmer_ids"]),
                    "known_area_hectares": round(item["known_area_hectares"], 2),
                    "farms_with_area": item["farms_with_area"],
                }
                for item in sorted(
                    grouped.values(),
                    key=lambda value: len(value["farm_ids"]),
                    reverse=True,
                )
            ]

        by_crop = group_rows(lambda farm: farm.crop)
        by_location = group_rows(
            lambda farm: " / ".join(
                part
                for part in (
                    getattr(locations.get(farm.id), "district", None),
                    getattr(locations.get(farm.id), "village", None),
                )
                if part
            )
            or None
        )

        stage_by_farm: dict[uuid.UUID, str] = {}
        if farm_ids:
            sessions = (
                await self.session.execute(
                    select(CropGrowthSession)
                    .where(
                        CropGrowthSession.farm_id.in_(farm_ids),
                        CropGrowthSession.is_deleted.is_(False),
                    )
                    .order_by(CropGrowthSession.updated_at)
                )
            ).scalars()
            for session in sessions:
                if session.current_growth_stage and session.current_growth_stage != "unknown":
                    stage_by_farm[session.farm_id] = session.current_growth_stage
            states = (
                await self.session.execute(
                    select(CropStageState)
                    .where(
                        CropStageState.farm_id.in_(farm_ids),
                        CropStageState.is_deleted.is_(False),
                    )
                    .order_by(CropStageState.updated_at)
                )
            ).scalars()
            for state in states:
                recorded = state.confirmed_stage or state.suggested_stage
                if recorded:
                    stage_by_farm[state.farm_id] = recorded
        stage_counts: dict[str, int] = {}
        for stage in stage_by_farm.values():
            stage_counts[stage] = stage_counts.get(stage, 0) + 1

        start = self.now.date()
        end = start + timedelta(days=harvest_days)
        offers = []
        if farm_ids:
            offers = list(
                (
                    await self.session.execute(
                        select(ProduceOffer).where(
                            ProduceOffer.farm_id.in_(farm_ids),
                            ProduceOffer.is_deleted.is_(False),
                            ProduceOffer.status.in_(
                                [ProduceStatus.SUBMITTED.value, ProduceStatus.PLANNED.value]
                            ),
                        )
                    )
                ).scalars()
            )
        window_offers = [
            offer for offer in offers
            if offer.expected_harvest_date is not None
            and start <= offer.expected_harvest_date <= end
        ]
        quantities: dict[str, float] = {}
        for offer in offers:
            amount = (
                offer.available_quantity
                if offer.available_quantity is not None
                else offer.quantity
            )
            quantities[offer.unit] = quantities.get(offer.unit, 0.0) + float(amount)

        known_area = sum(
            float(farm.area_hectares)
            for farm in farms
            if farm.area_hectares is not None
        )
        farms_with_area = sum(farm.area_hectares is not None for farm in farms)
        return {
            "generated_at": self.now,
            "filters": {
                "crop": crop,
                "district": district,
                "village": village,
                "harvest_days": harvest_days,
            },
            "summary": {
                "farmer_count": len({farm.user_id for farm in farms}),
                "farm_count": len(farms),
                "known_area_hectares": round(known_area, 2),
                "farms_with_area": farms_with_area,
                "farms_without_area": len(farms) - farms_with_area,
                "recorded_stage_farms": len(stage_by_farm),
                "sale_listing_count": len(offers),
                "harvest_window_farmer_count": len({offer.user_id for offer in window_offers}),
                "harvest_window_listing_count": len(window_offers),
            },
            "by_crop": by_crop,
            "by_location": by_location,
            "farm_records": [
                {
                    "farm_id": str(farm.id),
                    "name": farm.name,
                    "crop": farm.crop,
                    "district": getattr(locations.get(farm.id), "district", None),
                    "area_hectares": float(farm.area_hectares) if farm.area_hectares is not None else None,
                    "recorded_stage": stage_by_farm.get(farm.id),
                    "harvest_dates": sorted({
                        offer.expected_harvest_date for offer in offers
                        if offer.farm_id == farm.id and offer.expected_harvest_date is not None
                    }),
                }
                for farm in farms
            ],
            "crop_stages": [
                {"label": label, "farm_count": count}
                for label, count in sorted(
                    stage_counts.items(), key=lambda item: item[1], reverse=True
                )
            ],
            "offered_quantities": [
                {"unit": unit, "quantity": round(quantity, 2)}
                for unit, quantity in sorted(quantities.items())
            ],
            "harvest_window": {
                "from_date": start,
                "to_date": end,
                "farmer_count": len({offer.user_id for offer in window_offers}),
                "listing_count": len(window_offers),
            },
        }

    async def _farmer_growth(self, *, months: int) -> list[dict]:
        from app.modules.auth.profile_models import FarmerProfile

        out: list[dict] = []
        try:
            anchor = self.now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            buckets: list[tuple[datetime, datetime]] = []
            cursor = anchor
            for _ in range(months):
                nxt = cursor
                # Previous month start.
                prev_month = (cursor - timedelta(days=1)).replace(day=1)
                buckets.append((prev_month, nxt))
                cursor = prev_month
            for start, end in reversed(buckets):
                count = int(
                    (
                        await self.session.execute(
                            select(func.count())
                            .select_from(FarmerProfile)
                            .where(
                                FarmerProfile.created_at >= start,
                                FarmerProfile.created_at < end,
                            )
                        )
                    ).scalar_one()
                )
                out.append({"label": start.strftime("%Y-%m"), "count": count})
        except Exception:  # noqa: BLE001
            logger.exception("admin farmer growth failed")
        return out
