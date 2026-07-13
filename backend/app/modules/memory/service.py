"""Farm Memory service (docs: Repository → Service → Memory Engine → Provider → API).

``rebuild`` reads every module (guarded), runs the pure engine to merge duplicate
events, assign importance, generate seasonal/yearly summaries and link related
memories, then persists the new memories (immutably — existing history is never
rewritten). Reads serve the dashboard / latest / history / summary / detail. Business
logic lives here; routes stay thin.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.auth.models import User
from app.modules.farms.models import Farm
from app.modules.farms.repositories import FarmRepository
from app.modules.memory.engine import (
    MemoryFacts,
    RebuildResult,
    generate_summaries,
    link_memories,
    merge_drafts,
    select_new,
)
from app.modules.memory.exceptions import FarmNotOwnedError, MemoryNotFoundError
from app.modules.memory.models import (
    FarmMemory,
    MemoryEvent,
    MemoryLink,
    MemoryTag,
)
from app.modules.memory.repository import MemoryRepository
from app.modules.memory.sources import MemorySources
from app.schemas.response import PaginatedData

logger = get_logger("memory.service")


class MemoryService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        weather_service=None,  # noqa: ANN001 — optional WeatherService (best-effort)
        now: datetime | None = None,
        enable_weather: bool = True,
    ) -> None:
        self.session = session
        self.repo = MemoryRepository(session)
        self.farms = FarmRepository(session)
        self.weather_service = weather_service
        self.enable_weather = enable_weather
        self._now = now

    def _now_dt(self) -> datetime:
        return self._now or datetime.now(UTC)

    async def _require_farm(self, user: User, farm_id: uuid.UUID) -> Farm:
        farm = await self.farms.get_for_user(farm_id, user.id)
        if farm is None:
            raise FarmNotOwnedError()
        return farm

    # ----------------------------------------------------------------- #
    # Rebuild
    # ----------------------------------------------------------------- #
    async def rebuild(self, user: User, farm_id: uuid.UUID) -> RebuildResult:
        farm = await self._require_farm(user, farm_id)
        now = self._now_dt()

        sources = MemorySources(
            self.session,
            now=now,
            weather_service=self.weather_service,
            enable_weather=self.enable_weather,
        )
        drafts = await sources.gather(user, farm)

        merged = merge_drafts(drafts)
        existing = await self.repo.existing_keys(user.id)
        new = select_new(merged, existing)

        result = RebuildResult()
        for m in new:
            lead = m.lead
            memory = FarmMemory(
                user_id=user.id,
                farm_id=farm.id,
                source_module=lead.source_module,
                event_type=lead.event_type,
                summary=lead.summary,
                params=lead.params or None,
                detail=lead.detail,
                confidence=lead.confidence,
                importance=lead.importance,
                importance_score=lead.importance_score,
                observation=lead.observation,
                season=lead.season,
                season_year=lead.season_year,
                crop=lead.crop,
                location=lead.location,
                source_ref=lead.source_ref,
                dedup_key=m.key,
                occurred_at=lead.occurred_at,
            )
            await self.repo.add_memory(memory)
            for d in m.drafts:
                await self.repo.add_event(
                    MemoryEvent(
                        memory_id=memory.id,
                        user_id=user.id,
                        farm_id=farm.id,
                        source_module=d.source_module,
                        event_type=d.event_type,
                        confidence=d.confidence,
                        payload=d.params or None,
                        occurred_at=d.occurred_at,
                    )
                )
            for tag in dict.fromkeys(lead.tags):  # de-duplicate, preserve order
                if tag:
                    await self.repo.add_tag(MemoryTag(memory_id=memory.id, tag=tag[:48]))
            result.created += 1
            result.new_keys.append(m.key)

        # Regenerate derived artefacts over the full (immutable) memory set.
        memories = await self.repo.all_for_farm(user.id, farm.id)
        key_to_id = {mem.dedup_key: mem.id for mem in memories}
        facts = [
            MemoryFacts(
                key=mem.dedup_key,
                source_module=mem.source_module,
                event_type=mem.event_type,
                importance=mem.importance,
                season=mem.season,
                season_year=mem.season_year,
                crop=mem.crop,
                occurred_at=mem.occurred_at,
            )
            for mem in memories
        ]

        for draft in generate_summaries(facts, generated_at=now):
            draft = _map_highlights(draft, key_to_id)
            await self.repo.upsert_summary(draft, user_id=user.id, farm_id=farm.id)
            result.summaries += 1

        existing_links = await self.repo.existing_link_sigs(user.id)
        for link in link_memories(facts):
            a = key_to_id.get(link.from_key)
            b = key_to_id.get(link.to_key)
            if a is None or b is None:
                continue
            sig = (str(a), str(b), link.link_type)
            if sig in existing_links:
                continue
            await self.repo.add_link(
                MemoryLink(
                    user_id=user.id,
                    from_memory_id=a,
                    to_memory_id=b,
                    link_type=link.link_type,
                )
            )
            existing_links.add(sig)
            result.links += 1

        result.total = len(memories)
        await self.session.flush()
        logger.info(
            "Memory rebuild user=%s farm=%s: +%s new (%s total, %s summaries, %s links)",
            user.id, farm.id, result.created, result.total, result.summaries, result.links,
        )
        return result

    # ----------------------------------------------------------------- #
    # Reads
    # ----------------------------------------------------------------- #
    async def get_dashboard(self, user: User, farm_id: uuid.UUID) -> dict:
        await self._require_farm(user, farm_id)
        total = await self.repo.count_for_farm(user.id, farm_id)
        rows, _ = await self.repo.list_timeline(user.id, farm_id, limit=5, offset=0)
        summaries = await self.repo.list_summaries(user.id, farm_id)
        return {
            "farm_id": farm_id,
            "has_data": total > 0,
            "total": total,
            "message_code": None if total else "memory.status.no_memory",
            "recent": rows,
            "latest_summary": summaries[0] if summaries else None,
        }

    async def latest(self, user: User, farm_id: uuid.UUID) -> FarmMemory:
        await self._require_farm(user, farm_id)
        memory = await self.repo.latest_memory(user.id, farm_id)
        if memory is None:
            raise MemoryNotFoundError()
        return memory

    async def history(
        self,
        user: User,
        farm_id: uuid.UUID,
        *,
        page: int,
        page_size: int,
        source_module: str | None = None,
        season: str | None = None,
        crop: str | None = None,
        importance: str | None = None,
        search: str | None = None,
    ) -> PaginatedData[FarmMemory]:
        await self._require_farm(user, farm_id)
        offset = (page - 1) * page_size
        rows, total = await self.repo.list_timeline(
            user.id,
            farm_id,
            source_module=source_module,
            season=season,
            crop=crop,
            importance=importance,
            search=search,
            limit=page_size,
            offset=offset,
        )
        total_pages = (total + page_size - 1) // page_size if total else 0
        return PaginatedData(
            items=rows, page=page, page_size=page_size, total=total, total_pages=total_pages
        )

    async def summaries(self, user: User, farm_id: uuid.UUID):  # noqa: ANN201
        await self._require_farm(user, farm_id)
        return await self.repo.list_summaries(user.id, farm_id)

    async def get_memory(
        self, user: User, memory_id: uuid.UUID
    ) -> tuple[FarmMemory, list[MemoryLink]]:
        memory = await self.repo.get_memory(memory_id, user.id)
        if memory is None:
            raise MemoryNotFoundError()
        links = await self.repo.links_for(user.id, memory_id)
        return memory, links


def _map_highlights(draft, key_to_id):  # noqa: ANN001, ANN201
    """Convert highlight dedup-keys to stable memory ids for the client."""
    from dataclasses import replace

    ids = [str(key_to_id[k]) for k in draft.highlights if k in key_to_id]
    return replace(draft, highlights=ids)
