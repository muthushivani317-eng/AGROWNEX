"""Structured memory-event drafts (pure inputs to the Farm Memory Engine).

A ``MemoryEventDraft`` is the deterministic, structured representation of one real
thing that happened on a farm, produced by a collector from a source module's own
records. It is never fabricated — a collector emits a draft only when a real record
exists. The engine merges duplicate drafts, assigns importance and links them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.modules.memory.constants import (
    DEDUP_DATE_FMT,
    IMPORTANCE_SCORE,
    Importance,
    ObservationKind,
    season_for_month,
    season_year,
)


@dataclass(frozen=True)
class MemoryEventDraft:
    source_module: str
    event_type: str
    occurred_at: datetime
    summary: str                       # localization code, e.g. memory.event.disease_diagnosed
    importance: str = Importance.LOW.value
    observation: str = ObservationKind.OBSERVED.value
    confidence: int | None = None
    crop: str | None = None
    location: str | None = None
    source_ref: str | None = None
    params: dict = field(default_factory=dict)
    detail: str | None = None
    tags: tuple[str, ...] = ()

    @property
    def importance_score(self) -> int:
        return IMPORTANCE_SCORE.get(self.importance, 0)

    @property
    def season(self) -> str:
        return season_for_month(self.occurred_at.month)

    @property
    def season_year(self) -> int:
        return season_year(self.occurred_at.year, self.occurred_at.month)

    def dedup_key(self) -> str:
        """A stable key so rebuild is idempotent and history is immutable.

        Same source + event + crop + day ⇒ one canonical memory (duplicate events
        merge). A ``source_ref`` (e.g. a specific report id) keeps genuinely distinct
        same-day events apart.
        """
        day = self.occurred_at.strftime(DEDUP_DATE_FMT)
        crop = (self.crop or "-").lower()
        ref = self.source_ref or day
        return f"{self.source_module}:{self.event_type}:{crop}:{ref}"
