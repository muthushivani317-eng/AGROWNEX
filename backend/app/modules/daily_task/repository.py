"""Data-access layer for the Today's Farm Task feature. Thin, explicit
queries -- no business logic (that lives in ranking_engine.py / service.py).
Follows the existing repository pattern used across the app (e.g.
`app/modules/farms/repositories.py`).
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.daily_task.constants import TaskStatus
from app.modules.daily_task.models import (
    DailySignal,
    DailyTask,
    DailyTaskAuditLog,
    DailyTaskResponse,
    DailyTaskZone,
    EvidencePack,
)


class DailyTaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_signal(self, **kwargs) -> DailySignal:
        signal = DailySignal(**kwargs)
        self.session.add(signal)
        await self.session.flush()
        return signal

    async def get_signal(self, signal_id: uuid.UUID) -> DailySignal | None:
        result = await self.session.execute(select(DailySignal).where(DailySignal.id == signal_id))
        return result.scalar_one_or_none()

    async def create_task(self, **kwargs) -> DailyTask:
        task = DailyTask(**kwargs)
        self.session.add(task)
        await self.session.flush()
        return task

    async def get_task(self, task_id: uuid.UUID) -> DailyTask | None:
        result = await self.session.execute(select(DailyTask).where(DailyTask.id == task_id))
        return result.scalar_one_or_none()

    async def get_task_by_signal_id(self, signal_id: uuid.UUID) -> DailyTask | None:
        """`daily_tasks.signal_id` is unique (one card per signal) -- used by
        `DailyTaskService.generate_tasks_for_farm` to make a same-day re-run
        (worker restart, manual retrigger) a genuine no-op for a signal that
        already produced a card, instead of hitting that unique constraint.
        """
        result = await self.session.execute(select(DailyTask).where(DailyTask.signal_id == signal_id))
        return result.scalar_one_or_none()

    async def get_active_tasks_for_user(self, user_id: uuid.UUID) -> list[DailyTask]:
        result = await self.session.execute(
            select(DailyTask)
            .where(DailyTask.user_id == user_id, DailyTask.status == TaskStatus.ACTIVE.value)
            .order_by(DailyTask.rank_position)
        )
        return list(result.scalars().all())

    async def get_history_for_user(
        self, user_id: uuid.UUID, *, limit: int = 20, before: dt.datetime | None = None
    ) -> list[DailyTask]:
        stmt = (
            select(DailyTask)
            .where(
                DailyTask.user_id == user_id,
                DailyTask.status.in_([TaskStatus.RESPONDED.value, TaskStatus.EXPIRED.value]),
            )
            .order_by(DailyTask.created_at.desc())
            .limit(limit)
        )
        if before:
            stmt = stmt.where(DailyTask.created_at < before)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_last_task_for_field_and_type(self, farm_id: uuid.UUID, task_type) -> DailyTask | None:
        result = await self.session.execute(
            select(DailyTask)
            .where(DailyTask.farm_id == farm_id, DailyTask.task_type == task_type.value)
            .order_by(DailyTask.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_final_response(self, task_id: uuid.UUID) -> str | None:
        result = await self.session.execute(
            select(DailyTaskResponse.response_type)
            .where(DailyTaskResponse.task_id == task_id)
            .order_by(DailyTaskResponse.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_responses(self, task_id: uuid.UUID) -> list[DailyTaskResponse]:
        result = await self.session.execute(
            select(DailyTaskResponse)
            .where(DailyTaskResponse.task_id == task_id)
            .order_by(DailyTaskResponse.created_at)
        )
        return list(result.scalars().all())

    async def add_response(self, task_id: uuid.UUID, **kwargs) -> DailyTaskResponse:
        response = DailyTaskResponse(task_id=task_id, **kwargs)
        self.session.add(response)
        await self.session.flush()
        return response

    async def append_photo_to_response(self, response_id: uuid.UUID, object_id: str) -> None:
        result = await self.session.execute(
            select(DailyTaskResponse).where(DailyTaskResponse.id == response_id)
        )
        response = result.scalar_one()
        response.photo_object_ids = [*response.photo_object_ids, object_id]
        await self.session.flush()

    async def set_voice_note_on_response(self, response_id: uuid.UUID, object_id: str) -> None:
        await self.session.execute(
            update(DailyTaskResponse)
            .where(DailyTaskResponse.id == response_id)
            .values(voice_note_object_id=object_id)
        )

    async def update_task_status(self, task_id: uuid.UUID, status: TaskStatus, **extra) -> None:
        await self.session.execute(
            update(DailyTask).where(DailyTask.id == task_id).values(status=status.value, **extra)
        )

    async def expire_stale_active_tasks(self, *, now: dt.datetime) -> int:
        result = await self.session.execute(
            update(DailyTask)
            .where(DailyTask.status == TaskStatus.ACTIVE.value, DailyTask.valid_until < now)
            .values(status=TaskStatus.EXPIRED.value)
            .returning(DailyTask.id)
        )
        return len(result.fetchall())

    async def get_responded_tasks_due_for_verification(
        self, *, now: dt.datetime, after_hours: int = 20
    ) -> list[DailyTask]:
        cutoff = now - dt.timedelta(hours=after_hours)
        result = await self.session.execute(
            select(DailyTask).where(
                DailyTask.status == TaskStatus.RESPONDED.value,
                DailyTask.verification_followup_sent_at.is_(None),
                DailyTask.updated_at <= cutoff,
            )
        )
        return list(result.scalars().all())

    async def mark_verification_sent(self, task_id: uuid.UUID, *, sent_at: dt.datetime) -> None:
        await self.session.execute(
            update(DailyTask).where(DailyTask.id == task_id).values(verification_followup_sent_at=sent_at)
        )

    async def get_signal_by_dedupe_key_and_date(
        self, dedupe_key: str, observed_date: dt.date
    ) -> DailySignal | None:
        result = await self.session.execute(
            select(DailySignal).where(
                DailySignal.dedupe_key == dedupe_key,
                DailySignal.observed_at >= dt.datetime.combine(observed_date, dt.time.min, tzinfo=dt.UTC),
                DailySignal.observed_at < dt.datetime.combine(observed_date, dt.time.max, tzinfo=dt.UTC),
            )
        )
        return result.scalar_one_or_none()

    async def update_signal_status(
        self, signal_id: uuid.UUID, *, status: str, status_reason: str | None = None
    ) -> None:
        values: dict = {"status": status}
        if status_reason is not None:
            values["status_reason"] = status_reason[:2000]
        await self.session.execute(update(DailySignal).where(DailySignal.id == signal_id).values(**values))

    async def create_evidence_pack(self, **kwargs) -> EvidencePack:
        pack = EvidencePack(**kwargs)
        self.session.add(pack)
        await self.session.flush()
        return pack

    async def update_evidence_pack_content(self, pack_id: uuid.UUID, *, content: dict) -> None:
        await self.session.execute(
            update(EvidencePack).where(EvidencePack.id == pack_id).values(content=content)
        )

    async def get_evidence_pack(self, pack_id: uuid.UUID) -> EvidencePack | None:
        result = await self.session.execute(select(EvidencePack).where(EvidencePack.id == pack_id))
        return result.scalar_one_or_none()

    async def mark_evidence_pack_shared(self, pack_id: uuid.UUID, target: str) -> None:
        pack = await self.get_evidence_pack(pack_id)
        if pack is None:
            return
        shared = [*pack.shared_with, target] if target not in pack.shared_with else pack.shared_with
        await self.session.execute(
            update(EvidencePack)
            .where(EvidencePack.id == pack_id)
            .values(shared_with=shared, status="shared")
        )

    async def write_audit_log(self, *, run_id: uuid.UUID, farm_id: uuid.UUID, entries: list[dict]) -> None:
        for entry in entries:
            self.session.add(
                DailyTaskAuditLog(
                    run_id=run_id,
                    farm_id=farm_id,
                    signal_id=entry.get("signal_id"),
                    decision=entry["decision"],
                    decision_detail=entry["decision_detail"],
                )
            )
        await self.session.flush()

    async def get_audit_entries_for_signal(self, signal_id: uuid.UUID) -> list[dict]:
        result = await self.session.execute(
            select(DailyTaskAuditLog)
            .where(DailyTaskAuditLog.signal_id == signal_id)
            .order_by(DailyTaskAuditLog.created_at)
        )
        return [
            {"decision": row.decision, "decision_detail": row.decision_detail, "created_at": row.created_at.isoformat()}
            for row in result.scalars().all()
        ]


class DailyTaskZoneRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_source_zone(self, farm_id: uuid.UUID, source_zone_id: str) -> DailyTaskZone | None:
        result = await self.session.execute(
            select(DailyTaskZone).where(
                DailyTaskZone.farm_id == farm_id,
                DailyTaskZone.source_zone_id == source_zone_id,
                DailyTaskZone.status.in_(["watching", "confirmed"]),
            )
        )
        return result.scalar_one_or_none()

    async def create_zone(self, **kwargs) -> DailyTaskZone:
        zone = DailyTaskZone(**kwargs)
        self.session.add(zone)
        await self.session.flush()
        return zone

    async def update_zone_confirmation(self, zone_id: uuid.UUID, **kwargs) -> None:
        await self.session.execute(update(DailyTaskZone).where(DailyTaskZone.id == zone_id).values(**kwargs))

    async def list_confirmed_zones(self, farm_id: uuid.UUID) -> list[DailyTaskZone]:
        result = await self.session.execute(
            select(DailyTaskZone).where(DailyTaskZone.farm_id == farm_id, DailyTaskZone.status == "confirmed")
        )
        return list(result.scalars().all())

    async def expire_unconfirmed_zones_older_than(self, farm_id: uuid.UUID, *, days: int) -> None:
        cutoff = dt.datetime.now(dt.UTC) - dt.timedelta(days=days)
        await self.session.execute(
            update(DailyTaskZone)
            .where(
                DailyTaskZone.farm_id == farm_id,
                DailyTaskZone.status == "watching",
                DailyTaskZone.last_confirmed_at < cutoff,
            )
            .values(status="resolved")
        )
