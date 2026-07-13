"""Calendar repository (docs/BACKEND_ARCHITECTURE.md → Repository Pattern).

The only layer that queries ``crop_calendar_events``. Always scoped by
``user_id`` and excludes soft-deleted rows.
"""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Select, func, select

from app.modules.calendar.constants import EventStatus
from app.modules.calendar.models import CalendarEvent
from app.shared.base_repository import BaseRepository


class CalendarEventRepository(BaseRepository[CalendarEvent]):
    model = CalendarEvent

    def _filtered(
        self,
        user_id: uuid.UUID,
        *,
        farm_id: uuid.UUID | None = None,
        crop: str | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> Select[tuple[CalendarEvent]]:
        stmt = select(CalendarEvent).where(
            CalendarEvent.user_id == user_id,
            CalendarEvent.is_deleted.is_(False),
        )
        if farm_id is not None:
            stmt = stmt.where(CalendarEvent.farm_id == farm_id)
        if crop:
            stmt = stmt.where(CalendarEvent.crop == crop)
        if status:
            stmt = stmt.where(CalendarEvent.status == status)
        if date_from is not None:
            stmt = stmt.where(CalendarEvent.scheduled_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(CalendarEvent.scheduled_date <= date_to)
        return stmt

    async def list_events(
        self,
        user_id: uuid.UUID,
        *,
        farm_id: uuid.UUID | None = None,
        crop: str | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[CalendarEvent]:
        stmt = (
            self._filtered(
                user_id,
                farm_id=farm_id,
                crop=crop,
                status=status,
                date_from=date_from,
                date_to=date_to,
            )
            .order_by(
                CalendarEvent.scheduled_date.asc(),
                CalendarEvent.day_offset.asc(),
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_missed(
        self,
        user_id: uuid.UUID,
        *,
        today: date,
        farm_id: uuid.UUID | None = None,
        crop: str | None = None,
    ) -> list[CalendarEvent]:
        """Pending activities whose scheduled date is already past."""
        stmt = (
            self._filtered(
                user_id,
                farm_id=farm_id,
                crop=crop,
                status=EventStatus.PENDING.value,
            )
            .where(CalendarEvent.scheduled_date < today)
            .order_by(CalendarEvent.scheduled_date.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_for_user(
        self, event_id: uuid.UUID, user_id: uuid.UUID
    ) -> CalendarEvent | None:
        result = await self.session.execute(
            select(CalendarEvent).where(
                CalendarEvent.id == event_id,
                CalendarEvent.user_id == user_id,
                CalendarEvent.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def add_all(self, events: list[CalendarEvent]) -> list[CalendarEvent]:
        self.session.add_all(events)
        await self.session.flush()
        return events

    async def soft_delete_for_farm(
        self, user_id: uuid.UUID, farm_id: uuid.UUID
    ) -> int:
        """Soft-delete a farm's existing pending calendar before regenerating.

        Completed/skipped history is preserved so progress is not lost.
        """
        events = await self.list_events(
            user_id, farm_id=farm_id, status=EventStatus.PENDING.value
        )
        for event in events:
            event.is_deleted = True
        await self.session.flush()
        return len(events)

    async def status_counts(
        self, user_id: uuid.UUID, *, farm_id: uuid.UUID | None = None
    ) -> dict[str, int]:
        stmt = (
            self._filtered(user_id, farm_id=farm_id)
            .with_only_columns(CalendarEvent.status, func.count())
            .order_by(None)
            .group_by(CalendarEvent.status)
        )
        result = await self.session.execute(stmt)
        return {status: int(count) for status, count in result.all()}
