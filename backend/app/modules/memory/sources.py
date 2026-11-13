"""Memory sources — the I/O boundary between the Farm Memory Engine and the modules.

Each ``_read_*`` adapter reads one module through its **own repository/service** (no
source module is modified) and turns real records into structured ``MemoryEventDraft``s
via the pure collectors. Every adapter is guarded so a single module failing never
breaks a rebuild — it just contributes no memories. Nothing is fabricated: a draft is
produced only when a real record exists (docs/PRODUCT_RULES.md).
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.auth.models import User
from app.modules.farms.models import Farm
from app.modules.memory import collectors
from app.modules.memory.signals import MemoryEventDraft

logger = get_logger("memory.sources")

# Bound how many historical records each source contributes per rebuild.
_LIMIT = 50

_SATELLITE_DECLINE = ("declining",)
_EXPERT_RESOLVED = ("resolved", "closed")


class MemorySources:
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
        self.weather_service = weather_service
        self.enable_weather = enable_weather

    async def gather(self, user: User, farm: Farm) -> list[MemoryEventDraft]:
        drafts: list[MemoryEventDraft] = []
        for name, fn in (
            ("disease", self._read_disease),
            ("nutrient", self._read_nutrient),
            ("soil", self._read_soil),
            ("satellite", self._read_satellite),
            ("growth", self._read_growth),
            ("calendar", self._read_calendar),
            ("produce", self._read_produce),
            ("experts", self._read_experts),
            ("schemes", self._read_schemes),
            ("market", self._read_market),
            ("ai_chat", self._read_ai_chat),
            ("weather", self._read_weather),
        ):
            drafts.extend(await self._guard(name, fn, user, farm))
        return drafts

    async def _guard(self, name, fn, user, farm) -> list[MemoryEventDraft]:  # noqa: ANN001
        try:
            return await fn(user, farm)
        except Exception:  # noqa: BLE001 — one module must never break a rebuild
            logger.exception("memory source '%s' failed; skipping", name)
            return []

    def _location(self, farm: Farm) -> str | None:
        loc = getattr(farm, "location", None)
        for attr in ("village", "block", "district"):
            val = getattr(loc, attr, None)
            if val:
                return val
        return None

    # ----------------------------------------------------------------- #
    async def _read_disease(self, user: User, farm: Farm) -> list[MemoryEventDraft]:
        from app.modules.disease.repositories import DiseaseReportRepository

        reports = await DiseaseReportRepository(self.session).list_for_user(
            user.id, limit=_LIMIT, offset=0, farm_id=farm.id
        )
        out: list[MemoryEventDraft] = []
        for r in reports:
            draft = collectors.collect_disease(
                occurred_at=r.created_at,
                disease=r.disease,
                confidence=r.confidence,
                severity=r.severity,
                crop=r.crop or getattr(farm, "crop", None),
                needs_expert=bool(r.needs_expert_review),
                source_ref=str(r.id),
            )
            if draft:
                out.append(self._with_location(draft, farm))
        return out

    async def _read_nutrient(self, user: User, farm: Farm) -> list[MemoryEventDraft]:
        from app.modules.nutrient.repository import NutrientRepository
        from app.modules.nutrient.safety import consumer_safe_nutrient_finding

        reports, _ = await NutrientRepository(self.session).list_reports(
            user.id, farm.id, limit=_LIMIT, offset=0
        )
        out: list[MemoryEventDraft] = []
        for r in reports:
            a = r.analysis
            if a is None:
                continue
            safe = consumer_safe_nutrient_finding(
                crop=r.crop or getattr(farm, "crop", None),
                primary_deficiency=a.primary_deficiency,
                status=a.status,
                confidence=a.confidence,
                needs_test=bool(a.needs_test),
                needs_expert=bool(a.needs_expert),
            )
            draft = collectors.collect_nutrient(
                occurred_at=r.created_at,
                primary=safe.primary_deficiency,
                status=safe.status,
                confidence=safe.confidence,
                severity=a.severity,
                crop=r.crop or getattr(farm, "crop", None),
                needs_test=safe.needs_test,
                source_ref=str(r.id),
            )
            if draft:
                out.append(self._with_location(draft, farm))
        return out

    async def _read_soil(self, user: User, farm: Farm) -> list[MemoryEventDraft]:
        from app.modules.soil.repository import SoilRepository

        reports, _ = await SoilRepository(self.session).list_reports(
            user.id, farm.id, limit=_LIMIT, offset=0
        )
        out: list[MemoryEventDraft] = []
        for r in reports:
            draft = collectors.collect_soil(
                occurred_at=r.created_at,
                source=getattr(r, "source", None),
                confidence=getattr(r, "confidence", None),
                crop=getattr(farm, "crop", None),
                source_ref=str(r.id),
            )
            out.append(self._with_location(draft, farm))
        return out

    async def _read_satellite(self, user: User, farm: Farm) -> list[MemoryEventDraft]:
        from app.modules.satellite.repository import SatelliteRepository

        sessions, _ = await SatelliteRepository(self.session).list_sessions(
            user.id, farm.id, limit=_LIMIT, offset=0
        )
        out: list[MemoryEventDraft] = []
        for s in sessions:
            if s.status != "available":
                continue
            declining = (
                s.trend in _SATELLITE_DECLINE
                or s.vegetation_health in ("bare", "very_low", "low")
                or (s.stress_level in ("moderate", "severe"))
            )
            occurred = (
                datetime(s.capture_date.year, s.capture_date.month, s.capture_date.day, tzinfo=UTC)
                if getattr(s, "capture_date", None)
                else s.created_at
            )
            draft = collectors.collect_satellite(
                occurred_at=occurred,
                vegetation_health=s.vegetation_health,
                trend=s.trend,
                stress_level=s.stress_level,
                declining=declining,
                ndvi=s.ndvi,
                crop=getattr(farm, "crop", None),
                source_ref=str(s.id),
            )
            out.append(self._with_location(draft, farm))
        return out

    async def _read_growth(self, user: User, farm: Farm) -> list[MemoryEventDraft]:
        from app.modules.growth.repository import GrowthRepository

        repo = GrowthRepository(self.session)
        sessions, _ = await repo.list_sessions(user.id, farm_id=farm.id, limit=_LIMIT, offset=0)
        out: list[MemoryEventDraft] = []
        for s in sessions:
            timeline = await repo.latest_timeline_entry(s.id)
            draft = collectors.collect_growth(
                occurred_at=s.created_at,
                health_score=getattr(s, "latest_health_score", None)
                or (timeline.health_score if timeline else None),
                health_delta=timeline.health_delta if timeline else None,
                risk_level=getattr(s, "latest_risk_level", None)
                or (timeline.risk_level if timeline else None),
                crop=getattr(s, "crop", None) or getattr(farm, "crop", None),
                source_ref=str(s.id),
            )
            out.append(self._with_location(draft, farm))
        return out

    async def _read_calendar(self, user: User, farm: Farm) -> list[MemoryEventDraft]:
        from app.modules.calendar.repositories import CalendarEventRepository

        events = await CalendarEventRepository(self.session).list_events(
            user.id, farm_id=farm.id, status="completed", limit=_LIMIT
        )
        draft = collectors.collect_calendar_completed(
            occurred_at=self.now,
            completed_count=len(events),
            crop=getattr(farm, "crop", None),
        )
        return [self._with_location(draft, farm)] if draft else []

    async def _read_produce(self, user: User, farm: Farm) -> list[MemoryEventDraft]:
        from app.modules.produce.repository import ProduceRepository

        offers, _ = await ProduceRepository(self.session).list_for_user(
            user.id, farm_id=farm.id, limit=_LIMIT, offset=0
        )
        out: list[MemoryEventDraft] = []
        for o in offers:
            draft = collectors.collect_harvest(
                occurred_at=o.created_at,
                crop=getattr(o, "commodity", None) or getattr(o, "crop", None)
                or getattr(farm, "crop", None),
                quantity=o.quantity,
                unit=o.unit,
                source_ref=str(o.id),
            )
            out.append(self._with_location(draft, farm))
        return out

    async def _read_experts(self, user: User, farm: Farm) -> list[MemoryEventDraft]:
        from app.modules.experts.repository import ExpertRepository

        rows, _ = await ExpertRepository(self.session).list_consultations(
            user.id, limit=_LIMIT, offset=0
        )
        out: list[MemoryEventDraft] = []
        for c in rows:
            if getattr(c, "farm_id", None) != farm.id:
                continue
            resolved = c.status in _EXPERT_RESOLVED
            occurred = (c.resolved_at if resolved and c.resolved_at else c.created_at)
            draft = collectors.collect_expert(
                occurred_at=occurred,
                resolved=resolved,
                subject=c.subject,
                crop=c.crop or getattr(farm, "crop", None),
                source_ref=str(c.id),
            )
            out.append(self._with_location(draft, farm))
        return out

    async def _read_schemes(self, user: User, farm: Farm) -> list[MemoryEventDraft]:
        from app.modules.schemes.repository import SchemeRepository

        repo = SchemeRepository(self.session)
        bookmarks = await repo.list_bookmarks(user.id)
        if not bookmarks:
            return []
        schemes = await repo.schemes_by_ids([b.scheme_id for b in bookmarks])
        titles = {s.id: s.title for s in schemes}
        out: list[MemoryEventDraft] = []
        for b in bookmarks:
            draft = collectors.collect_scheme(
                occurred_at=b.created_at,
                title=titles.get(b.scheme_id),
                source_ref=str(b.id),
            )
            out.append(self._with_location(draft, farm))
        return out

    async def _read_market(self, user: User, farm: Farm) -> list[MemoryEventDraft]:
        from app.modules.market.repository import MarketRepository

        favourites = await MarketRepository(self.session).list_favourites(user.id)
        out: list[MemoryEventDraft] = []
        for f in favourites:
            draft = collectors.collect_market(
                occurred_at=f.created_at,
                crop=getattr(f, "commodity", None),
                source_ref=str(f.id),
            )
            out.append(self._with_location(draft, farm))
        return out

    async def _read_ai_chat(self, user: User, farm: Farm) -> list[MemoryEventDraft]:
        from app.modules.ai.repositories import ConversationRepository

        convos = await ConversationRepository(self.session).list_for_user(
            user.id, limit=_LIMIT, offset=0
        )
        out: list[MemoryEventDraft] = []
        for c in convos:
            if getattr(c, "farm_id", None) not in (farm.id, None):
                continue
            draft = collectors.collect_ai_chat(
                occurred_at=getattr(c, "started_at", None) or c.created_at,
                title=c.title,
                source_ref=str(c.id),
            )
            out.append(self._with_location(draft, farm))
        return out

    async def _read_weather(self, user: User, farm: Farm) -> list[MemoryEventDraft]:
        if not self.enable_weather or self.weather_service is None:
            return []
        location = getattr(farm, "location", None)
        if location is None or location.latitude is None or location.longitude is None:
            return []
        bundle = await self.weather_service.get_by_farm(user, farm.id)
        draft = collectors.collect_weather(
            occurred_at=self.now,
            insight_codes=tuple(i.code for i in bundle.insights),
            crop=getattr(farm, "crop", None),
        )
        return [self._with_location(draft, farm)] if draft else []

    def _with_location(self, draft: MemoryEventDraft, farm: Farm) -> MemoryEventDraft:
        if draft.location is not None:
            return draft
        loc = self._location(farm)
        if loc is None:
            return draft
        # dataclass is frozen — rebuild with the resolved location.
        from dataclasses import replace

        return replace(draft, location=loc)
