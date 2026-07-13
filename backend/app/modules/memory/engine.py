"""Farm Memory Engine (pure — docs: merge duplicates, importance, summaries, links).

No I/O. Given the structured drafts a farm produced (from ``collectors``) and the
memories already stored, it decides:

* which drafts are **new** (idempotent, immutable history — a draft whose ``dedup_key``
  already exists is never re-created),
* how duplicate drafts **merge** into one canonical memory,
* **seasonal** and **yearly** summaries (counts, dominant source, top importance), and
* deterministic **links** between related memories (follows / relates / resolves) —
  the seed of a future farm knowledge graph.

Nothing here fabricates data: summaries and links are derived only from real memories.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from app.modules.memory.constants import (
    IMPORTANCE_ORDER,
    EventType,
    Importance,
    LinkType,
    SummaryPeriod,
)
from app.modules.memory.signals import MemoryEventDraft


@dataclass(frozen=True)
class MergedMemory:
    """One canonical memory + the raw drafts that merged into it."""

    key: str
    lead: MemoryEventDraft
    drafts: tuple[MemoryEventDraft, ...]

    @property
    def occurrences(self) -> int:
        return len(self.drafts)


def merge_drafts(drafts: list[MemoryEventDraft]) -> list[MergedMemory]:
    """Collapse duplicate drafts (same ``dedup_key``) into one memory each.

    The highest-importance (then highest-confidence) draft leads; the rest are kept
    as contributing events. Result is ordered newest-first by occurrence time.
    """
    buckets: dict[str, list[MemoryEventDraft]] = defaultdict(list)
    for d in drafts:
        buckets[d.dedup_key()].append(d)

    merged: list[MergedMemory] = []
    for key, group in buckets.items():
        lead = max(
            group,
            key=lambda d: (
                IMPORTANCE_ORDER.get(d.importance, 0),
                d.confidence or 0,
                d.occurred_at.timestamp(),
            ),
        )
        ordered = tuple(sorted(group, key=lambda d: d.occurred_at))
        merged.append(MergedMemory(key=key, lead=lead, drafts=ordered))

    merged.sort(key=lambda m: m.lead.occurred_at, reverse=True)
    return merged


def select_new(
    merged: list[MergedMemory], existing_keys: set[str]
) -> list[MergedMemory]:
    """Keep only memories whose key is not already stored (immutable history)."""
    return [m for m in merged if m.key not in existing_keys]


# --------------------------------------------------------------------------- #
# Summaries
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class SummaryDraft:
    period_type: str
    period_key: str
    season: str | None
    year: int
    crop: str | None
    summary: str                       # localization code
    params: dict
    highlights: list[str]              # dedup keys of the most important memories
    event_count: int
    importance: str
    generated_at: datetime


@dataclass(frozen=True)
class MemoryFacts:
    """A minimal projection of a stored memory the engine reasons over (pure)."""

    key: str
    source_module: str
    event_type: str
    importance: str
    season: str | None
    season_year: int | None
    crop: str | None
    occurred_at: datetime


def _dominant(values: list[str]) -> str | None:
    if not values:
        return None
    counts: dict[str, int] = defaultdict(int)
    for v in values:
        counts[v] += 1
    return max(counts, key=lambda k: (counts[k], k))


def _top_importance(values: list[str]) -> str:
    best = Importance.LOW.value
    for v in values:
        if IMPORTANCE_ORDER.get(v, 0) > IMPORTANCE_ORDER.get(best, 0):
            best = v
    return best


def generate_summaries(
    facts: list[MemoryFacts], *, generated_at: datetime
) -> list[SummaryDraft]:
    """Seasonal + yearly summaries from all stored memories (pure, reproducible)."""
    seasons: dict[tuple[int, str], list[MemoryFacts]] = defaultdict(list)
    years: dict[int, list[MemoryFacts]] = defaultdict(list)

    for f in facts:
        year = f.season_year if f.season_year is not None else f.occurred_at.year
        if f.season:
            seasons[(year, f.season)].append(f)
        years[year].append(f)

    drafts: list[SummaryDraft] = []

    for (year, season), items in seasons.items():
        drafts.append(
            _summary_for(
                items,
                period_type=SummaryPeriod.SEASON.value,
                period_key=f"{year}-{season}",
                season=season,
                year=year,
                generated_at=generated_at,
            )
        )
    for year, items in years.items():
        drafts.append(
            _summary_for(
                items,
                period_type=SummaryPeriod.YEAR.value,
                period_key=str(year),
                season=None,
                year=year,
                generated_at=generated_at,
            )
        )

    drafts.sort(key=lambda d: (d.year, d.period_type, d.period_key), reverse=True)
    return drafts


def _summary_for(
    items: list[MemoryFacts],
    *,
    period_type: str,
    period_key: str,
    season: str | None,
    year: int,
    generated_at: datetime,
) -> SummaryDraft:
    modules = [i.source_module for i in items]
    crops = [i.crop for i in items if i.crop]
    importances = [i.importance for i in items]
    dominant_module = _dominant(modules)
    dominant_crop = _dominant(crops)
    top_importance = _top_importance(importances)

    # Highlight the most important memories (importance desc, then most recent).
    highlights = [
        f.key
        for f in sorted(
            items,
            key=lambda f: (IMPORTANCE_ORDER.get(f.importance, 0), f.occurred_at),
            reverse=True,
        )[:3]
    ]

    disease_count = sum(1 for i in items if i.source_module == "disease")
    return SummaryDraft(
        period_type=period_type,
        period_key=period_key,
        season=season,
        year=year,
        crop=dominant_crop,
        summary="memory.summary.period",
        params={
            "season": season,
            "year": year,
            "crop": dominant_crop,
            "dominant_module": dominant_module,
            "disease_count": disease_count,
        },
        highlights=highlights,
        event_count=len(items),
        importance=top_importance,
        generated_at=generated_at,
    )


# --------------------------------------------------------------------------- #
# Links (deterministic knowledge-graph edges)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class LinkDraft:
    from_key: str
    to_key: str
    link_type: str


# Which resolution event_type resolves which prior event_type.
_RESOLVES: dict[str, str] = {
    EventType.EXPERT_CONSULTATION_RESOLVED.value: EventType.DISEASE_DIAGNOSED.value,
    EventType.DISEASE_RESOLVED.value: EventType.DISEASE_DIAGNOSED.value,
}


def link_memories(facts: list[MemoryFacts]) -> list[LinkDraft]:
    """Relate memories deterministically (pure).

    * ``follows``  — each memory follows the previous one from the same module.
    * ``relates``  — cross-module memories sharing the same crop + season.
    * ``resolves`` — a resolution event resolves the most recent matching prior issue.
    """
    ordered = sorted(facts, key=lambda f: f.occurred_at)
    links: list[LinkDraft] = []
    seen: set[tuple[str, str, str]] = set()

    def _add(a: str, b: str, t: str) -> None:
        if a == b:
            return
        sig = (a, b, t)
        if sig in seen:
            return
        seen.add(sig)
        links.append(LinkDraft(from_key=a, to_key=b, link_type=t))

    # follows: previous memory of the same source module
    last_by_module: dict[str, MemoryFacts] = {}
    for f in ordered:
        prev = last_by_module.get(f.source_module)
        if prev is not None:
            _add(f.key, prev.key, LinkType.FOLLOWS.value)
        last_by_module[f.source_module] = f

    # relates: same crop + season, different module (link to the nearest earlier one)
    for idx, f in enumerate(ordered):
        if not f.crop or not f.season:
            continue
        for g in reversed(ordered[:idx]):
            if (
                g.crop == f.crop
                and g.season == f.season
                and g.season_year == f.season_year
                and g.source_module != f.source_module
            ):
                _add(f.key, g.key, LinkType.RELATES.value)
                break

    # resolves: a resolution resolves the most recent matching prior issue
    for idx, f in enumerate(ordered):
        target = _RESOLVES.get(f.event_type)
        if not target:
            continue
        for g in reversed(ordered[:idx]):
            if g.event_type == target and (g.crop == f.crop or f.crop is None):
                _add(f.key, g.key, LinkType.RESOLVES.value)
                break

    return links


@dataclass
class RebuildResult:
    created: int = 0
    total: int = 0
    summaries: int = 0
    links: int = 0
    new_keys: list[str] = field(default_factory=list)
