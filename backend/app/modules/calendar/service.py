"""Calendar service — deterministic generation + read-time weather advisories.

API → Service → Repository. Reuses the farm repository (ownership) and the
weather service (insights) — it never re-implements weather or farm logic.
"""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.auth.models import User
from app.modules.calendar.constants import (
    DEFAULT_REMINDER_HOUR,
    DEFAULT_UPCOMING_DAYS,
    WEATHER_ADVISORY_HORIZON_DAYS,
    EventStatus,
    WeatherAdvisory,
    WeatherDependency,
)
from app.modules.calendar.exceptions import (
    CalendarEventNotFoundError,
    FarmNotFoundError,
    SowingDateRequiredError,
)
from app.modules.calendar.generator import derive_season, generate_events
from app.modules.calendar.models import CalendarEvent
from app.modules.calendar.repositories import CalendarEventRepository
from app.modules.calendar.schemas import (
    CalendarSummaryOut,
    GenerateCalendarRequest,
    UpdateCalendarEventRequest,
)
from app.modules.calendar.weather_adjuster import advisory_for, codes_from_bundle
from app.modules.farms.models import Farm
from app.modules.farms.repositories import FarmRepository
from app.modules.weather.service import WeatherService

logger = get_logger("calendar.service")

# An annotated event: the row plus its read-time weather advisory (advisory value).
AnnotatedEvent = tuple[CalendarEvent, str]


class CalendarService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        weather_service: WeatherService | None = None,
    ) -> None:
        self.session = session
        self.events = CalendarEventRepository(session)
        self.farms = FarmRepository(session)
        self.weather_service = weather_service

    # ----- Generation -----
    async def generate(
        self, user: User, req: GenerateCalendarRequest
    ) -> list[AnnotatedEvent]:
        farm = await self._require_farm(user, req.farm_id)
        crop = req.crop or farm.crop
        sowing_date = req.sowing_date or farm.sowing_date
        irrigation_type = req.irrigation_type or farm.irrigation_type
        if sowing_date is None:
            raise SowingDateRequiredError()

        season = derive_season(sowing_date)
        generated = generate_events(
            crop,
            sowing_date,
            irrigation_type=irrigation_type,
            reminders_enabled=req.reminders_enabled,
        )

        # Regenerate idempotently: drop the old pending plan, keep completed history.
        await self.events.soft_delete_for_farm(user.id, farm.id)

        rows = [
            CalendarEvent(
                user_id=user.id,
                farm_id=farm.id,
                code=g.code,
                activity_type=g.activity_type.value,
                title=g.title,
                description=g.description,
                scheduled_date=g.scheduled_date,
                day_offset=g.day_offset,
                crop=crop,
                season=season.value,
                growth_stage=g.growth_stage,
                priority=g.priority.value,
                status=EventStatus.PENDING.value,
                weather_dependency=g.weather_dependency.value,
                reminder_enabled=g.reminder_enabled,
                reminder_hour=DEFAULT_REMINDER_HOUR if g.reminder_enabled else None,
            )
            for g in generated
        ]
        await self.events.add_all(rows)
        logger.info(
            "Generated %d calendar activities for farm=%s user=%s",
            len(rows),
            farm.id,
            user.id,
        )
        return await self._annotate(user, rows)

    # ----- Reads -----
    async def timeline(
        self,
        user: User,
        *,
        farm_id: uuid.UUID | None = None,
        crop: str | None = None,
        status: str | None = None,
    ) -> list[AnnotatedEvent]:
        if farm_id is not None:
            await self._require_farm(user, farm_id)
        events = await self.events.list_events(
            user.id, farm_id=farm_id, crop=crop, status=status
        )
        return await self._annotate(user, events)

    async def for_farm(
        self, user: User, farm_id: uuid.UUID
    ) -> list[AnnotatedEvent]:
        await self._require_farm(user, farm_id)
        events = await self.events.list_events(user.id, farm_id=farm_id)
        return await self._annotate(user, events)

    async def today(
        self, user: User, *, farm_id: uuid.UUID | None = None
    ) -> list[AnnotatedEvent]:
        if farm_id is not None:
            await self._require_farm(user, farm_id)
        current = self._today()
        events = await self.events.list_events(
            user.id, farm_id=farm_id, date_from=current, date_to=current
        )
        return await self._annotate(user, events)

    async def upcoming(
        self,
        user: User,
        *,
        farm_id: uuid.UUID | None = None,
        days: int = DEFAULT_UPCOMING_DAYS,
    ) -> list[AnnotatedEvent]:
        if farm_id is not None:
            await self._require_farm(user, farm_id)
        current = self._today()
        events = await self.events.list_events(
            user.id,
            farm_id=farm_id,
            status=EventStatus.PENDING.value,
            date_from=current,
            date_to=current + timedelta(days=days),
        )
        return await self._annotate(user, events)

    async def completed(
        self, user: User, *, farm_id: uuid.UUID | None = None
    ) -> list[AnnotatedEvent]:
        if farm_id is not None:
            await self._require_farm(user, farm_id)
        events = await self.events.list_events(
            user.id, farm_id=farm_id, status=EventStatus.DONE.value
        )
        return await self._annotate(user, events)

    async def missed(
        self, user: User, *, farm_id: uuid.UUID | None = None
    ) -> list[AnnotatedEvent]:
        if farm_id is not None:
            await self._require_farm(user, farm_id)
        events = await self.events.list_missed(
            user.id, today=self._today(), farm_id=farm_id
        )
        return await self._annotate(user, events)

    async def summary(self, user: User, farm_id: uuid.UUID) -> CalendarSummaryOut:
        farm = await self._require_farm(user, farm_id)
        counts = await self.events.status_counts(user.id, farm_id=farm_id)
        missed = await self.events.list_missed(
            user.id, today=self._today(), farm_id=farm_id
        )
        season = None
        crop = farm.crop
        if farm.sowing_date is not None:
            season = derive_season(farm.sowing_date).value
        return CalendarSummaryOut(
            farm_id=farm_id,
            crop=crop,
            season=season,
            total=sum(counts.values()),
            completed=counts.get(EventStatus.DONE.value, 0),
            pending=counts.get(EventStatus.PENDING.value, 0),
            missed=len(missed),
            skipped=counts.get(EventStatus.SKIPPED.value, 0),
        )

    # ----- Mutation (offline completion sync) -----
    async def update_event(
        self, user: User, event_id: uuid.UUID, req: UpdateCalendarEventRequest
    ) -> AnnotatedEvent:
        event = await self.events.get_for_user(event_id, user.id)
        if event is None:
            raise CalendarEventNotFoundError()
        if req.status is not None:
            event.status = req.status
            event.completed_at = (
                datetime.now(UTC) if req.status == EventStatus.DONE.value else None
            )
        if req.reminder_enabled is not None:
            event.reminder_enabled = req.reminder_enabled
        if req.notes is not None:
            event.notes = req.notes
        await self.session.flush()
        annotated = await self._annotate(user, [event])
        return annotated[0]

    # ----- Helpers -----
    async def _require_farm(self, user: User, farm_id: uuid.UUID) -> Farm:
        farm = await self.farms.get_for_user(farm_id, user.id)
        if farm is None:
            raise FarmNotFoundError()
        return farm

    @staticmethod
    def _today() -> date:
        return datetime.now(UTC).date()

    async def _annotate(
        self, user: User, events: list[CalendarEvent]
    ) -> list[AnnotatedEvent]:
        """Attach a read-time weather advisory to each event (reuses weather).

        Weather is fetched once per farm, best-effort. Only pending tasks that
        depend on weather and fall inside the forecast horizon are annotated.
        """
        if not events:
            return []
        horizon = self._today() + timedelta(days=WEATHER_ADVISORY_HORIZON_DAYS)
        codes_by_farm: dict[uuid.UUID, set[str]] = {}
        annotated: list[AnnotatedEvent] = []
        for event in events:
            advisory = WeatherAdvisory.NONE.value
            relevant = (
                event.status == EventStatus.PENDING.value
                and event.weather_dependency != WeatherDependency.NONE.value
                and event.scheduled_date <= horizon
            )
            if relevant:
                codes = await self._farm_insight_codes(user, event.farm_id, codes_by_farm)
                advisory = advisory_for(
                    WeatherDependency(event.weather_dependency), codes
                ).value
            annotated.append((event, advisory))
        return annotated

    async def _farm_insight_codes(
        self,
        user: User,
        farm_id: uuid.UUID,
        cache: dict[uuid.UUID, set[str]],
    ) -> set[str]:
        if farm_id in cache:
            return cache[farm_id]
        codes: set[str] = set()
        if self.weather_service is not None:
            try:
                bundle = await self.weather_service.get_by_farm(user, farm_id)
                codes = codes_from_bundle(bundle)
            except Exception:
                logger.info("weather advisory unavailable for farm=%s", farm_id)
        cache[farm_id] = codes
        return codes
