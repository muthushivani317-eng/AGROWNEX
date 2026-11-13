"""Event sources (docs: the engine "receives events from every completed module").

``NotificationSources`` is the I/O boundary between the notification engine and the
rest of AgrowAI. Each ``_collect_*`` adapter reads one completed module through its
**own repository/service** (the source modules are never modified) and builds the
pure collector views; the pure collectors then emit ``CandidateEvent``s. Every
source is wrapped so a single module failing (or the weather network being down)
never breaks generation — resilience mirrors the Market module's offline fallback.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.ai.repositories import ConversationRepository
from app.modules.auth.models import User
from app.modules.calendar.repositories import CalendarEventRepository
from app.modules.disease.repositories import DiseaseReportRepository
from app.modules.disease_risk.engine import RiskEvaluation, RiskOutcome
from app.modules.disease_risk.models import DiseaseRiskAlert
from app.modules.farms.repositories import FarmRepository
from app.modules.growth.repository import GrowthRepository
from app.modules.market.repository import MarketRepository
from app.modules.notifications.collectors import (
    AIActivityView,
    CalendarCounts,
    DiseaseReportView,
    ExpertConsultationView,
    GrowthView,
    IntelligenceReportView,
    MarketMoveView,
    NutrientReportView,
    OutbreakView,
    ProduceOfferView,
    SatelliteSessionView,
    SchemeView,
    SoilReportView,
    WeatherSnapshot,
    collect_ai,
    collect_calendar,
    collect_disease,
    collect_disease_risk_conditions,
    collect_experts,
    collect_growth,
    collect_intelligence,
    collect_market,
    collect_nutrient,
    collect_outbreak,
    collect_produce,
    collect_satellite,
    collect_schemes,
    collect_soil,
    collect_weather,
)
from app.modules.notifications.constants import UPCOMING_TASK_WINDOW_DAYS
from app.modules.notifications.engine import CandidateEvent
from app.modules.produce.constants import ProduceStatus
from app.modules.produce.repository import ProduceRepository

logger = get_logger("notifications.sources")

_UPCOMING_PRODUCE = (ProduceStatus.SUBMITTED.value, ProduceStatus.PLANNED.value)

# Satellite alert codes that constitute a "vegetation decline" notification.
_SATELLITE_VEGETATION_CODES = frozenset(
    {
        "satellite.alert.vegetation_decline",
        "satellite.alert.rapid_ndvi_drop",
        "satellite.alert.abnormal_seasonal_change",
        "satellite.alert.low_vigor",
        "satellite.alert.moisture_stress",
    }
)


class NotificationSources:
    def __init__(
        self,
        session: AsyncSession,
        *,
        now: datetime,
        enable_weather: bool = True,
        outbreak_index: dict[str, list[tuple[str, str]]] | None = None,
    ) -> None:
        self.session = session
        self.now = now
        self.today: date = now.date()
        self.enable_weather = enable_weather
        self._outbreak_index = outbreak_index or {}

    async def collect(self, user: User) -> list[CandidateEvent]:
        """Run every source; a failing source is logged and skipped, never fatal."""
        events: list[CandidateEvent] = []
        for name, adapter in (
            ("calendar", self._collect_calendar),
            ("disease", self._collect_disease),
            ("outbreak", self._collect_outbreak),
            ("growth", self._collect_growth),
            ("market", self._collect_market),
            ("schemes", self._collect_schemes),
            ("produce", self._collect_produce),
            ("ai", self._collect_ai),
            ("experts", self._collect_experts),
            ("soil", self._collect_soil),
            ("satellite", self._collect_satellite),
            ("nutrient", self._collect_nutrient),
            ("intelligence", self._collect_intelligence),
            ("weather", self._collect_weather),
        ):
            try:
                events.extend(await adapter(user))
            except Exception:  # noqa: BLE001 — resilience: one source must not break sync
                logger.exception("notification source '%s' failed; skipping", name)
        return events

    # ----------------------------------------------------------------- #
    def _days_since(self, moment: datetime | None) -> int | None:
        if moment is None:
            return None
        return (self.today - moment.date()).days

    # ----------------------------------------------------------------- #
    async def _collect_calendar(self, user: User) -> list[CandidateEvent]:
        from datetime import timedelta

        from app.modules.calendar.registry import ACTIVE_CROP_STAGE_REGISTRY

        repo = CalendarEventRepository(self.session)
        # Counts per farm for today / the upcoming window / missed.
        today_events = await repo.list_events(
            user.id, status="pending", date_from=self.today, date_to=self.today
        )
        upcoming_events = await repo.list_events(
            user.id,
            status="pending",
            date_from=self.today + timedelta(days=1),
            date_to=self.today + timedelta(days=UPCOMING_TASK_WINDOW_DAYS),
        )
        missed_events = await repo.list_missed(user.id, today=self.today)

        buckets: dict[str | None, CalendarCounts] = {}

        def _bucket(farm_id: uuid.UUID | None) -> str | None:
            return str(farm_id) if farm_id else None

        def _ensure(fid: str | None) -> CalendarCounts:
            if fid not in buckets:
                buckets[fid] = CalendarCounts(farm_id=fid or "none")
            return buckets[fid]

        def _is_current_verified(ev) -> bool:
            schedule = ACTIVE_CROP_STAGE_REGISTRY.resolve(ev.crop)
            return bool(
                schedule
                and ev.registry_verification_status == "VERIFIED"
                and ev.registry_version == schedule.version
                and ev.registry_content_hash == schedule.content_hash
            )

        for ev in filter(_is_current_verified, today_events):
            fid = _bucket(ev.farm_id)
            cur = _ensure(fid)
            buckets[fid] = CalendarCounts(
                farm_id=cur.farm_id, today=cur.today + 1, upcoming=cur.upcoming, missed=cur.missed
            )
        for ev in filter(_is_current_verified, upcoming_events):
            fid = _bucket(ev.farm_id)
            cur = _ensure(fid)
            buckets[fid] = CalendarCounts(
                farm_id=cur.farm_id, today=cur.today, upcoming=cur.upcoming + 1, missed=cur.missed
            )
        for ev in filter(_is_current_verified, missed_events):
            fid = _bucket(ev.farm_id)
            cur = _ensure(fid)
            buckets[fid] = CalendarCounts(
                farm_id=cur.farm_id, today=cur.today, upcoming=cur.upcoming, missed=cur.missed + 1
            )

        events: list[CandidateEvent] = []
        for counts in buckets.values():
            events.extend(collect_calendar(counts, day=self.today))
        return events

    # ----------------------------------------------------------------- #
    async def _collect_disease(self, user: User) -> list[CandidateEvent]:
        repo = DiseaseReportRepository(self.session)
        reports = await repo.list_for_user(user.id, limit=50, offset=0)
        events: list[CandidateEvent] = []
        for r in reports:
            view = DiseaseReportView(
                report_id=str(r.id),
                farm_id=str(r.farm_id) if r.farm_id else None,
                crop=r.crop,
                disease=r.disease,
                confidence=r.confidence,
                needs_expert_review=bool(r.needs_expert_review),
                quality_poor=False,  # poor images are rejected before storage
            )
            events.extend(collect_disease(view))
        from sqlalchemy import select

        risks = list(
            (
                await self.session.execute(
                    select(DiseaseRiskAlert).where(
                        DiseaseRiskAlert.user_id == user.id,
                        DiseaseRiskAlert.status == "RISK_CONDITIONS_PRESENT",
                    )
                )
            ).scalars()
        )
        for risk in risks:
            evaluation = RiskEvaluation(
                outcome=RiskOutcome.RISK_CONDITIONS_PRESENT,
                matched_conditions=risk.weather_factors,
                rule_pack_id=risk.rule_pack_id,
                rule_pack_version=risk.rule_version,
                evaluated_at=risk.generated_at,
            )
            events.extend(
                collect_disease_risk_conditions(
                    evaluation,
                    farm_id=str(risk.farm_id),
                    crop_id=risk.crop,
                    disease_id=risk.disease_key or "unknown",
                )
            )
        return events

    async def _collect_outbreak(self, user: User) -> list[CandidateEvent]:
        if not self._outbreak_index:
            return []
        farms = await FarmRepository(self.session).list_for_user(user.id, limit=50, offset=0)
        districts = {
            farm.location.district.strip().lower()
            for farm in farms
            if farm.location and farm.location.district
        }
        events: list[CandidateEvent] = []
        for district in districts:
            for crop, disease in self._outbreak_index.get(district, []):
                events.extend(
                    collect_outbreak(
                        OutbreakView(
                            district=district,
                            crop=crop,
                            disease=disease,
                        ),
                        week=self.today,
                    )
                )
        return events

    # ----------------------------------------------------------------- #
    async def _collect_growth(self, user: User) -> list[CandidateEvent]:
        repo = GrowthRepository(self.session)
        sessions = await repo.active_sessions_for_user(user.id)
        events: list[CandidateEvent] = []
        for session in sessions:
            latest_image = await repo.latest_image_for_session(session.id)
            latest_timeline = await repo.latest_timeline_entry(session.id)
            view = GrowthView(
                session_id=str(session.id),
                farm_id=str(session.farm_id) if session.farm_id else None,
                week_number=latest_image.week_number if latest_image else 1,
                last_image_days_ago=self._days_since(
                    latest_image.captured_at if latest_image else None
                ),
                current_growth_stage=session.current_growth_stage,
                latest_health_delta=(latest_timeline.health_delta if latest_timeline else None),
                latest_timeline_id=(str(latest_timeline.id) if latest_timeline else None),
            )
            events.extend(collect_growth(view))
        return events

    # ----------------------------------------------------------------- #
    async def _collect_market(self, user: User) -> list[CandidateEvent]:
        from datetime import timedelta

        repo = MarketRepository(self.session)
        favourites = await repo.list_favourites(user.id)
        events: list[CandidateEvent] = []
        for fav in favourites:
            latest = await repo.latest_price(
                commodity=fav.commodity, market=fav.market_name, district=fav.district
            )
            if latest is None:
                continue
            price_row, _location = latest
            _loc, history = await repo.history(
                commodity=fav.commodity,
                market=fav.market_name,
                district=fav.district,
                date_from=self.today - timedelta(days=7),
            )
            change_percent: float | None = None
            if len(history) >= 2 and history[0].modal_price:
                first = history[0].modal_price
                change_percent = (price_row.modal_price - first) / first * 100.0
            is_period_high = bool(history) and price_row.modal_price >= max(
                h.modal_price for h in history
            )
            events.extend(
                collect_market(
                    MarketMoveView(
                        favourite_id=str(fav.id),
                        crop=fav.commodity,
                        market=fav.market_name,
                        latest_price=price_row.modal_price,
                        change_percent=change_percent,
                        is_period_high=is_period_high,
                    ),
                    day=self.today,
                )
            )
        return events

    # ----------------------------------------------------------------- #
    async def _collect_schemes(self, user: User) -> list[CandidateEvent]:
        # Import lazily to avoid any import cycle and keep this source optional.
        from app.modules.schemes.service import SchemeService

        service = SchemeService(self.session)
        page, _meta = await service.eligible(user, None, page=1, page_size=25)
        events: list[CandidateEvent] = []
        for item in page.items:
            days_to_deadline = (item.last_date - self.today).days if item.last_date else None
            view = SchemeView(
                scheme_id=str(item.id),
                title=item.title,
                days_to_deadline=days_to_deadline,
                is_newly_created=False,
            )
            events.extend(collect_schemes(view, now=self.now))
        return events

    # ----------------------------------------------------------------- #
    async def _collect_produce(self, user: User) -> list[CandidateEvent]:
        repo = ProduceRepository(self.session)
        offers, _total = await repo.list_for_user(
            user.id, statuses=_UPCOMING_PRODUCE, limit=200, offset=0
        )
        events: list[CandidateEvent] = []
        for offer in offers:
            days = (
                (offer.expected_harvest_date - self.today).days
                if offer.expected_harvest_date
                else None
            )
            events.extend(
                collect_produce(
                    ProduceOfferView(
                        offer_id=str(offer.id),
                        farm_id=str(offer.farm_id) if offer.farm_id else None,
                        crop=offer.crop_name,
                        days_to_harvest=days,
                        is_submitted=offer.status == ProduceStatus.SUBMITTED.value,
                    )
                )
            )
        return events

    # ----------------------------------------------------------------- #
    async def _collect_ai(self, user: User) -> list[CandidateEvent]:
        repo = ConversationRepository(self.session)
        conversations = await repo.list_for_user(user.id, limit=1, offset=0)
        if not conversations:
            return []
        latest = conversations[0]
        return collect_ai(
            AIActivityView(
                conversation_id=str(latest.id),
                days_since_last=self._days_since(latest.updated_at),
            ),
            day=self.today,
        )

    # ----------------------------------------------------------------- #
    async def _collect_experts(self, user: User) -> list[CandidateEvent]:
        from app.modules.experts.constants import ConsultationStatus, SenderType
        from app.modules.experts.repository import ExpertRepository

        repo = ExpertRepository(self.session)
        consultations = await repo.consultations_with_new_expert_activity(user.id)
        events: list[CandidateEvent] = []
        for c in consultations:
            expert_messages = [
                m
                for m in (c.messages or [])
                if m.sender_type == SenderType.EXPERT.value and not m.is_system
            ]
            latest_expert_message_id = str(expert_messages[-1].id) if expert_messages else None
            resolved_by_expert = c.status == ConsultationStatus.RESOLVED.value and any(
                h.new_status == ConsultationStatus.RESOLVED.value
                and h.changed_by_type == SenderType.EXPERT.value
                for h in (c.status_history or [])
            )
            events.extend(
                collect_experts(
                    ExpertConsultationView(
                        consultation_id=str(c.id),
                        subject=c.subject,
                        assigned=c.assigned_expert_id is not None,
                        expert_name=c.expert.full_name if c.expert else None,
                        latest_expert_message_id=latest_expert_message_id,
                        resolved_by_expert=resolved_by_expert,
                    )
                )
            )
        return events

    # ----------------------------------------------------------------- #
    async def _collect_soil(self, user: User) -> list[CandidateEvent]:
        from sqlalchemy import select

        from app.modules.soil.constants import ReportStatus
        from app.modules.soil.models import SoilRecommendation, SoilReport

        reports = (
            (
                await self.session.execute(
                    select(SoilReport)
                    .where(
                        SoilReport.user_id == user.id,
                        SoilReport.is_deleted.is_(False),
                        SoilReport.status == ReportStatus.PROCESSED.value,
                    )
                    .order_by(SoilReport.created_at.desc())
                    .limit(50)
                )
            )
            .scalars()
            .all()
        )

        events: list[CandidateEvent] = []
        for report in reports:
            severities = (
                (
                    await self.session.execute(
                        select(SoilRecommendation.severity).where(
                            SoilRecommendation.report_id == report.id
                        )
                    )
                )
                .scalars()
                .all()
            )
            deficiencies = [s for s in severities if s in ("warning", "critical")]
            events.extend(
                collect_soil(
                    SoilReportView(
                        report_id=str(report.id),
                        farm_id=str(report.farm_id),
                        source=report.source,
                        has_deficiency=bool(deficiencies),
                        deficiency_count=len(deficiencies),
                    )
                )
            )
        return events

    # ----------------------------------------------------------------- #
    async def _collect_satellite(self, user: User) -> list[CandidateEvent]:
        from app.modules.satellite.constants import SessionStatus
        from app.modules.satellite.repository import SatelliteRepository

        repo = SatelliteRepository(self.session)
        sessions = await repo.sessions_with_alerts(user.id)
        events: list[CandidateEvent] = []
        for sat in sessions:
            has_veg = any(a.code in _SATELLITE_VEGETATION_CODES for a in (sat.alerts or []))
            unavailable = sat.status == SessionStatus.UNAVAILABLE.value
            events.extend(
                collect_satellite(
                    SatelliteSessionView(
                        session_id=str(sat.id),
                        farm_id=str(sat.farm_id),
                        has_vegetation_alert=has_veg,
                        unavailable=unavailable,
                        unavailable_reason=sat.unavailable_reason,
                        observation_day=sat.created_at.date().isoformat(),
                    )
                )
            )
        return events

    # ----------------------------------------------------------------- #
    async def _collect_nutrient(self, user: User) -> list[CandidateEvent]:
        from app.modules.nutrient.constants import DeficiencyStatus
        from app.modules.nutrient.repository import NutrientRepository
        from app.modules.nutrient.safety import consumer_safe_nutrient_finding

        reports = await NutrientRepository(self.session).recent_reports(user.id, limit=50)
        events: list[CandidateEvent] = []
        for report in reports:
            analysis = report.analysis
            if analysis is None:
                continue
            safe = consumer_safe_nutrient_finding(
                crop=report.crop,
                primary_deficiency=analysis.primary_deficiency,
                status=analysis.status,
                confidence=analysis.confidence,
                needs_test=bool(analysis.needs_test),
                needs_expert=bool(analysis.needs_expert),
            )
            events.extend(
                collect_nutrient(
                    NutrientReportView(
                        report_id=str(report.id),
                        farm_id=str(report.farm_id),
                        primary_deficiency=safe.primary_deficiency,
                        confirmed=safe.status == DeficiencyStatus.CONFIRMED.value,
                        needs_test=safe.needs_test,
                    )
                )
            )
        return events

    # ----------------------------------------------------------------- #
    async def _collect_intelligence(self, user: User) -> list[CandidateEvent]:
        from app.modules.intelligence.repository import IntelligenceRepository

        reports = await IntelligenceRepository(self.session).recent_reports(user.id, limit=50)
        events: list[CandidateEvent] = []
        for report in reports:
            events.extend(
                collect_intelligence(
                    IntelligenceReportView(
                        report_id=str(report.id),
                        farm_id=str(report.farm_id),
                        overall_risk=report.overall_risk,
                        overall_health_score=report.overall_health_score,
                    )
                )
            )
        return events

    # ----------------------------------------------------------------- #
    async def _collect_weather(self, user: User) -> list[CandidateEvent]:
        if not self.enable_weather:
            return []
        # Import lazily — weather hits Open-Meteo (network). Guarded by collect().
        from app.modules.weather.service import WeatherService

        service = WeatherService(self.session)
        farms = await FarmRepository(self.session).list_for_user(user.id, limit=50, offset=0)
        events: list[CandidateEvent] = []
        for farm in farms:
            location = getattr(farm, "location", None)
            if location is None or location.latitude is None or location.longitude is None:
                continue
            bundle = await service.get_by_farm(user, farm.id)
            codes = [i.code for i in bundle.insights]
            daily_min = bundle.daily[0].temp_min_c if bundle.daily else None
            events.extend(
                collect_weather(
                    WeatherSnapshot(
                        farm_id=str(farm.id),
                        insight_codes=codes,
                        daily_min_temp_c=daily_min,
                    ),
                    day=self.today,
                )
            )
        return events
