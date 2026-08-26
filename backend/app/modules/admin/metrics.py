"""Admin metrics — read-only aggregation over every module (docs: dashboard/analytics).

The I/O boundary between the Admin Engine and the rest of AgrowAI. Every query is
read-only (docs: no direct farmer data modification) and guarded, so one module failing
never breaks the dashboard. Counts and group-bys are real — nothing is fabricated
(docs/PRODUCT_RULES.md → uncertainty is surfaced, e.g. untracked metrics stay ``None``).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

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
        from app.modules.nutrient.models import NutrientAnalysis

        try:
            d = (
                await self.session.execute(
                    select(func.avg(DiseaseReport.confidence)).where(
                        DiseaseReport.confidence.is_not(None)
                    )
                )
            ).scalar_one_or_none()
            n = (
                await self.session.execute(
                    select(func.avg(NutrientAnalysis.confidence)).where(
                        NutrientAnalysis.confidence.is_not(None)
                    )
                )
            ).scalar_one_or_none()
            vals = [v for v in (d, n) if v is not None]
            return round(sum(vals) / len(vals)) if vals else None
        except Exception:  # noqa: BLE001
            logger.exception("admin avg confidence failed")
            return None

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
        from app.modules.nutrient.models import NutrientAnalysis
        from app.modules.produce.models import ProduceOffer

        crop_distribution = await self._group(
            "crop", Farm.crop, select(Farm.crop, func.count()).where(Farm.is_deleted.is_(False))
        )
        disease_distribution = await self._group(
            "disease",
            DiseaseReport.disease,
            select(DiseaseReport.disease, func.count()).where(DiseaseReport.disease.is_not(None)),
        )
        nutrient_deficiencies = await self._group(
            "nutrient",
            NutrientAnalysis.primary_deficiency,
            select(NutrientAnalysis.primary_deficiency, func.count()).where(
                NutrientAnalysis.primary_deficiency.is_not(None)
            ),
        )
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
