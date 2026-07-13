"""Farm Memory repository (docs/BACKEND_ARCHITECTURE.md → Repository Pattern).

The only layer that queries the memory tables. Source-module data is read by the
sources through each module's own repository — never from here.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.memory.models import (
    FarmMemory,
    MemoryEvent,
    MemoryLink,
    MemorySummary,
    MemoryTag,
)


class MemoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _owned(self, user_id: uuid.UUID) -> Select[tuple[FarmMemory]]:
        return select(FarmMemory).where(
            FarmMemory.user_id == user_id,
            FarmMemory.is_deleted.is_(False),
        )

    # ----------------------------------------------------------------- #
    # Writes
    # ----------------------------------------------------------------- #
    async def add_memory(self, memory: FarmMemory) -> FarmMemory:
        self.session.add(memory)
        await self.session.flush()
        return memory

    async def add_event(self, event: MemoryEvent) -> MemoryEvent:
        self.session.add(event)
        await self.session.flush()
        return event

    async def add_tag(self, tag: MemoryTag) -> MemoryTag:
        self.session.add(tag)
        await self.session.flush()
        return tag

    async def add_link(self, link: MemoryLink) -> MemoryLink:
        self.session.add(link)
        await self.session.flush()
        return link

    async def upsert_summary(self, draft, *, user_id, farm_id) -> MemorySummary:  # noqa: ANN001
        existing = await self.get_summary(
            user_id, farm_id, draft.period_type, draft.period_key
        )
        if existing is None:
            summary = MemorySummary(
                user_id=user_id,
                farm_id=farm_id,
                period_type=draft.period_type,
                period_key=draft.period_key,
                season=draft.season,
                year=draft.year,
                crop=draft.crop,
                summary=draft.summary,
                params=draft.params,
                highlights=draft.highlights,
                event_count=draft.event_count,
                importance=draft.importance,
                generated_at=draft.generated_at,
            )
            self.session.add(summary)
            await self.session.flush()
            return summary
        existing.season = draft.season
        existing.crop = draft.crop
        existing.summary = draft.summary
        existing.params = draft.params
        existing.highlights = draft.highlights
        existing.event_count = draft.event_count
        existing.importance = draft.importance
        existing.generated_at = draft.generated_at
        await self.session.flush()
        return existing

    # ----------------------------------------------------------------- #
    # Reads
    # ----------------------------------------------------------------- #
    async def existing_keys(self, user_id: uuid.UUID) -> set[str]:
        rows = await self.session.execute(
            select(FarmMemory.dedup_key).where(FarmMemory.user_id == user_id)
        )
        return set(rows.scalars().all())

    async def get_memory(
        self, memory_id: uuid.UUID, user_id: uuid.UUID
    ) -> FarmMemory | None:
        res = await self.session.execute(
            self._owned(user_id).where(FarmMemory.id == memory_id)
        )
        return res.scalar_one_or_none()

    async def latest_memory(
        self, user_id: uuid.UUID, farm_id: uuid.UUID
    ) -> FarmMemory | None:
        res = await self.session.execute(
            self._owned(user_id)
            .where(FarmMemory.farm_id == farm_id)
            .order_by(FarmMemory.occurred_at.desc(), FarmMemory.created_at.desc())
            .limit(1)
        )
        return res.scalars().first()

    async def all_for_farm(
        self, user_id: uuid.UUID, farm_id: uuid.UUID, *, limit: int = 1000
    ) -> list[FarmMemory]:
        res = await self.session.execute(
            self._owned(user_id)
            .where(FarmMemory.farm_id == farm_id)
            .order_by(FarmMemory.occurred_at.desc())
            .limit(limit)
        )
        return list(res.scalars().unique().all())

    async def list_timeline(
        self,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
        *,
        source_module: str | None = None,
        season: str | None = None,
        crop: str | None = None,
        importance: str | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[FarmMemory], int]:
        base = self._owned(user_id).where(FarmMemory.farm_id == farm_id)
        if source_module:
            base = base.where(FarmMemory.source_module == source_module)
        if season:
            base = base.where(FarmMemory.season == season)
        if crop:
            base = base.where(FarmMemory.crop == crop)
        if importance:
            base = base.where(FarmMemory.importance == importance)
        if search:
            like = f"%{search.lower()}%"
            base = base.where(
                func.lower(FarmMemory.detail).like(like)
                | func.lower(FarmMemory.event_type).like(like)
            )

        total = int(
            (
                await self.session.execute(
                    select(func.count()).select_from(base.subquery())
                )
            ).scalar_one()
        )
        rows = (
            (
                await self.session.execute(
                    base.order_by(FarmMemory.occurred_at.desc(), FarmMemory.created_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .unique()
            .all()
        )
        return list(rows), total

    async def get_summary(
        self,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
        period_type: str,
        period_key: str,
    ) -> MemorySummary | None:
        res = await self.session.execute(
            select(MemorySummary).where(
                MemorySummary.user_id == user_id,
                MemorySummary.farm_id == farm_id,
                MemorySummary.period_type == period_type,
                MemorySummary.period_key == period_key,
                MemorySummary.is_deleted.is_(False),
            )
        )
        return res.scalar_one_or_none()

    async def list_summaries(
        self,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
        *,
        period_type: str | None = None,
    ) -> list[MemorySummary]:
        stmt = select(MemorySummary).where(
            MemorySummary.user_id == user_id,
            MemorySummary.farm_id == farm_id,
            MemorySummary.is_deleted.is_(False),
        )
        if period_type:
            stmt = stmt.where(MemorySummary.period_type == period_type)
        stmt = stmt.order_by(
            MemorySummary.year.desc(),
            MemorySummary.period_type.asc(),
            MemorySummary.period_key.desc(),
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def links_for(
        self, user_id: uuid.UUID, memory_id: uuid.UUID
    ) -> list[MemoryLink]:
        res = await self.session.execute(
            select(MemoryLink).where(
                MemoryLink.user_id == user_id,
                (MemoryLink.from_memory_id == memory_id)
                | (MemoryLink.to_memory_id == memory_id),
            )
        )
        return list(res.scalars().all())

    async def existing_link_sigs(self, user_id: uuid.UUID) -> set[tuple[str, str, str]]:
        res = await self.session.execute(
            select(
                MemoryLink.from_memory_id,
                MemoryLink.to_memory_id,
                MemoryLink.link_type,
            ).where(MemoryLink.user_id == user_id)
        )
        return {(str(a), str(b), t) for a, b, t in res.all()}

    async def count_for_farm(self, user_id: uuid.UUID, farm_id: uuid.UUID) -> int:
        res = await self.session.execute(
            select(func.count()).select_from(
                self._owned(user_id).where(FarmMemory.farm_id == farm_id).subquery()
            )
        )
        return int(res.scalar_one())
