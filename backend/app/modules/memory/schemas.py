"""Farm Memory request/response schemas (docs: reuse response envelope).

Summaries and event descriptions travel as localization ``summary`` codes + params so
the Tamil-first client renders them. Observed vs inferred is explicit. Missing data is
simply absent — never fabricated.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.modules.memory.models import (
    FarmMemory,
    MemoryLink,
    MemorySummary,
)
from app.modules.nutrient.crops import is_groundnut_nutrient_crop


class MemoryLinkOut(BaseModel):
    id: uuid.UUID
    from_memory_id: uuid.UUID
    to_memory_id: uuid.UUID
    link_type: str

    @classmethod
    def from_link(cls, link: MemoryLink) -> MemoryLinkOut:
        return cls(
            id=link.id,
            from_memory_id=link.from_memory_id,
            to_memory_id=link.to_memory_id,
            link_type=link.link_type,
        )


class MemoryOut(BaseModel):
    id: uuid.UUID
    farm_id: uuid.UUID
    source_module: str
    event_type: str
    summary: str
    params: dict | None
    confidence: int | None
    importance: str
    importance_score: int
    observation: str
    season: str | None
    season_year: int | None
    crop: str | None
    location: str | None
    occurred_at: datetime
    created_at: datetime
    tags: list[str]
    occurrences: int
    links: list[MemoryLinkOut]

    @classmethod
    def from_memory(
        cls, memory: FarmMemory, *, links: list[MemoryLink] | None = None
    ) -> MemoryOut:
        restricted = bool(
            memory.source_module == "nutrient"
            and is_groundnut_nutrient_crop(memory.crop)
            and (memory.params or {}).get("nutrient")
        )
        return cls(
            id=memory.id,
            farm_id=memory.farm_id,
            source_module=memory.source_module,
            event_type=memory.event_type,
            summary=(
                "memory.event.nutrient_review_required"
                if restricted
                else memory.summary
            ),
            params={} if restricted else memory.params,
            confidence=None if restricted else memory.confidence,
            importance=memory.importance,
            importance_score=memory.importance_score,
            observation=memory.observation,
            season=memory.season,
            season_year=memory.season_year,
            crop=memory.crop,
            location=memory.location,
            occurred_at=memory.occurred_at,
            created_at=memory.created_at,
            tags=(
                ["nutrient", "needs_test", "expert_review"]
                if restricted
                else [t.tag for t in memory.tags]
            ),
            occurrences=len(memory.events),
            links=[MemoryLinkOut.from_link(link) for link in (links or [])],
        )


class MemorySummaryOut(BaseModel):
    id: uuid.UUID
    farm_id: uuid.UUID
    period_type: str
    period_key: str
    season: str | None
    year: int
    crop: str | None
    summary: str
    params: dict | None
    highlights: list[str]
    event_count: int
    importance: str
    generated_at: datetime

    @classmethod
    def from_summary(cls, summary: MemorySummary) -> MemorySummaryOut:
        return cls(
            id=summary.id,
            farm_id=summary.farm_id,
            period_type=summary.period_type,
            period_key=summary.period_key,
            season=summary.season,
            year=summary.year,
            crop=summary.crop,
            summary=summary.summary,
            params=summary.params,
            highlights=list(summary.highlights or []),
            event_count=summary.event_count,
            importance=summary.importance,
            generated_at=summary.generated_at,
        )


class MemoryDashboardOut(BaseModel):
    farm_id: uuid.UUID
    has_data: bool
    total: int
    message_code: str | None
    recent: list[MemoryOut]
    latest_summary: MemorySummaryOut | None


class MemorySummaryBundleOut(BaseModel):
    farm_id: uuid.UUID
    seasons: list[MemorySummaryOut]
    years: list[MemorySummaryOut]


class MemoryRebuildOut(BaseModel):
    farm_id: uuid.UUID
    created: int
    total: int
    summaries: int
    links: int
