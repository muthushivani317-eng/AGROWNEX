"""Module readers (docs: aggregate outputs from every existing module).

``IntelligenceSources`` is the I/O boundary between the Crop Intelligence Engine and
the rest of AgrowAI. Each ``_read_*`` adapter reads one module through its **own
repository/service** (no source module is modified) and builds a pure signal. Every
adapter is guarded so a single module failing (or the weather network being down)
never breaks generation — it just lowers confidence.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.auth.models import User
from app.modules.farms.models import Farm
from app.modules.intelligence.constants import (
    SATELLITE_VEGETATION_ALERTS,
    SOURCE_FRESHNESS_DAYS,
)
from app.modules.intelligence.signals import (
    CalendarSignal,
    DiseaseSignal,
    ExpertSignal,
    GrowthSignal,
    IntelligenceInputs,
    NutrientSignal,
    SatelliteSignal,
    SoilSignal,
    WeatherSignal,
)

logger = get_logger("intelligence.sources")


class IntelligenceSources:
    def __init__(
        self,
        session: AsyncSession,
        *,
        now: datetime,
        weather_service=None,  # noqa: ANN001 — optional WeatherService (best-effort)
        enable_weather: bool = True,
    ) -> None:
        self.session = session
        self.now = now
        self.today: date = now.date()
        self.weather_service = weather_service
        self.enable_weather = enable_weather

    def _fresh(self, source: str, observed_at: datetime | date | None) -> bool:
        if observed_at is None:
            return False
        if isinstance(observed_at, date) and not isinstance(observed_at, datetime):
            observed = datetime.combine(observed_at, datetime.min.time(), tzinfo=UTC)
        else:
            observed = observed_at
            if observed.tzinfo is None:
                observed = observed.replace(tzinfo=UTC)
        return observed >= self.now - timedelta(days=SOURCE_FRESHNESS_DAYS[source])

    async def gather(self, user: User, farm: Farm) -> IntelligenceInputs:
        return IntelligenceInputs(
            disease=await self._guard("disease", self._read_disease, user, farm),
            nutrient=await self._guard("nutrient", self._read_nutrient, user, farm),
            soil=await self._guard("soil", self._read_soil, user, farm),
            satellite=await self._guard("satellite", self._read_satellite, user, farm),
            weather=await self._guard("weather", self._read_weather, user, farm),
            growth=await self._guard("growth", self._read_growth, user, farm),
            calendar=await self._guard("calendar", self._read_calendar, user, farm)
            or CalendarSignal(),
            expert=await self._guard("expert", self._read_expert, user, farm)
            or ExpertSignal(),
        )

    async def _guard(self, name, fn, user, farm):  # noqa: ANN001, ANN201
        try:
            return await fn(user, farm)
        except Exception:  # noqa: BLE001 — one module must never break aggregation
            logger.exception("intelligence source '%s' failed; skipping", name)
            return None

    # ----------------------------------------------------------------- #
    async def _read_disease(self, user: User, farm: Farm) -> DiseaseSignal | None:
        from app.modules.disease.repositories import DiseaseReportRepository

        reports = await DiseaseReportRepository(self.session).list_for_user(
            user.id, limit=1, offset=0, farm_id=farm.id
        )
        if not reports:
            return None
        r = reports[0]
        if not self._fresh("disease", r.created_at):
            return None
        return DiseaseSignal(
            disease=r.disease,
            confidence=r.confidence,
            severity=r.severity,
            needs_expert=bool(r.needs_expert_review),
        )

    async def _read_nutrient(self, user: User, farm: Farm) -> NutrientSignal | None:
        from app.modules.nutrient.repository import NutrientRepository
        from app.modules.nutrient.safety import consumer_safe_nutrient_finding

        report = await NutrientRepository(self.session).latest_report(user.id, farm.id)
        if report is None or report.analysis is None:
            return None
        observed_at = report.capture_date or report.created_at
        if not self._fresh("nutrient", observed_at):
            return None
        a = report.analysis
        safe = consumer_safe_nutrient_finding(
            crop=report.crop or getattr(farm, "crop", None),
            primary_deficiency=a.primary_deficiency,
            status=a.status,
            confidence=a.confidence,
            needs_test=bool(a.needs_test),
            needs_expert=bool(a.needs_expert),
        )
        return NutrientSignal(
            primary=safe.primary_deficiency,
            status=safe.status,
            confidence=safe.confidence,
            severity=a.severity,
            needs_test=safe.needs_test,
        )

    async def _read_soil(self, user: User, farm: Farm) -> SoilSignal | None:
        from app.modules.soil.repository import SoilRepository
        from app.modules.soil.service import SoilService

        assessment = await SoilService(self.session).assessment_for(user, farm.id)
        profile = await SoilRepository(self.session).get_profile(user.id, farm.id)
        if profile is None or not self._fresh(
            "soil", profile.last_test_date or profile.updated_at or profile.created_at
        ):
            return None
        has_data = assessment.has_any_value or bool(assessment.deficient_micronutrients)
        if not has_data:
            return None
        return SoilSignal(
            has_data=True,
            nitrogen=assessment.nitrogen,
            phosphorus=assessment.phosphorus,
            potassium=assessment.potassium,
            organic_carbon=assessment.organic_carbon,
            ph_class=assessment.ph_class,
            salinity=assessment.salinity,
            deficient_micronutrients=tuple(assessment.deficient_micronutrients),
            confidence=profile.confidence if profile else None,
        )

    async def _read_satellite(self, user: User, farm: Farm) -> SatelliteSignal | None:
        from app.modules.satellite.repository import SatelliteRepository

        repo = SatelliteRepository(self.session)
        session = await repo.latest_session(user.id, farm.id, available_only=True)
        if session is None:
            return None
        if not self._fresh("satellite", session.capture_date or session.created_at):
            return None
        alerts = await repo.list_alerts(session.id)
        codes = tuple(a.code for a in alerts if a.code in SATELLITE_VEGETATION_ALERTS)
        return SatelliteSignal(
            ndvi=session.ndvi,
            vegetation_health=session.vegetation_health,
            stress_level=session.stress_level,
            moisture_status=session.moisture_status,
            trend=session.trend,
            confidence=session.confidence,
            alert_codes=codes,
        )

    async def _read_weather(self, user: User, farm: Farm) -> WeatherSignal | None:
        if not self.enable_weather or self.weather_service is None:
            return None
        location = getattr(farm, "location", None)
        if location is None or location.latitude is None or location.longitude is None:
            return None
        bundle = await self.weather_service.get_by_farm(user, farm.id)
        daily = bundle.daily[0] if bundle.daily else None
        return WeatherSignal(
            insight_codes=tuple(i.code for i in bundle.insights),
            daily_min_temp_c=daily.temp_min_c if daily else None,
            daily_max_temp_c=daily.temp_max_c if daily else None,
            rain_probability_pct=daily.precipitation_probability_max_pct if daily else None,
        )

    async def _read_growth(self, user: User, farm: Farm) -> GrowthSignal | None:
        from app.modules.growth.repository import GrowthRepository

        repo = GrowthRepository(self.session)
        session = await repo.find_active_session(user.id, farm.id, None)
        if session is None:
            return None
        timeline = await repo.latest_timeline_entry(session.id)
        observed_at = (
            timeline.created_at
            if timeline is not None
            else session.updated_at or session.created_at
        )
        if not self._fresh("growth", observed_at):
            return None
        return GrowthSignal(
            health_score=session.latest_health_score
            or (timeline.health_score if timeline else None),
            health_delta=timeline.health_delta if timeline else None,
            risk_level=session.latest_risk_level
            or (timeline.risk_level if timeline else None),
        )

    async def _read_calendar(self, user: User, farm: Farm) -> CalendarSignal:
        from app.modules.calendar.repositories import CalendarEventRepository

        repo = CalendarEventRepository(self.session)
        fid = farm.id

        today_events = await repo.list_events(
            user.id, status="pending", date_from=self.today, date_to=self.today
        )
        upcoming_events = await repo.list_events(
            user.id,
            status="pending",
            date_from=self.today + timedelta(days=1),
            date_to=self.today + timedelta(days=3),
        )
        missed_events = await repo.list_missed(user.id, today=self.today)

        def _count(events) -> int:  # noqa: ANN001
            return sum(1 for e in events if e.farm_id == fid)

        return CalendarSignal(
            today=_count(today_events),
            upcoming=_count(upcoming_events),
            missed=_count(missed_events),
        )

    async def _read_expert(self, user: User, farm: Farm) -> ExpertSignal:
        from app.modules.experts.repository import ExpertRepository

        repo = ExpertRepository(self.session)
        _rows, total = await repo.list_consultations(
            user.id, statuses=repo.open_statuses(), limit=1, offset=0
        )
        return ExpertSignal(open_consultation=total > 0)
