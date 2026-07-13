"""Unit tests for the pure Farm Memory Engine + collectors (no I/O).

Covers season derivation, deterministic dedup, duplicate merging, importance
assignment, immutable-history selection, seasonal/yearly summary generation and the
deterministic knowledge-graph links (follows / relates / resolves).
"""
from __future__ import annotations

from datetime import UTC, datetime

from app.modules.memory import collectors
from app.modules.memory.constants import (
    EventType,
    Importance,
    LinkType,
    season_for_month,
    season_year,
)
from app.modules.memory.engine import (
    MemoryFacts,
    generate_summaries,
    link_memories,
    merge_drafts,
    select_new,
)


def _dt(y: int, m: int, d: int) -> datetime:
    return datetime(y, m, d, 6, 0, tzinfo=UTC)


# --------------------------------------------------------------------------- #
# Season derivation
# --------------------------------------------------------------------------- #
def test_season_for_month():
    assert season_for_month(7) == "kharif"
    assert season_for_month(11) == "rabi"
    assert season_for_month(1) == "rabi"
    assert season_for_month(4) == "summer"


def test_season_year_rabi_spans_boundary():
    # Jan/Feb belong to the previous agricultural year's Rabi season.
    assert season_year(2026, 1) == 2025
    assert season_year(2026, 7) == 2026


# --------------------------------------------------------------------------- #
# Collectors (pure)
# --------------------------------------------------------------------------- #
def test_collect_disease_importance_from_severity():
    high = collectors.collect_disease(
        occurred_at=_dt(2026, 7, 1), disease="Blast", confidence=90,
        severity="high", crop="paddy", needs_expert=True, source_ref="r1",
    )
    assert high is not None
    assert high.importance == Importance.CRITICAL.value
    assert high.observation == "observed"
    assert "needs_expert" in high.tags

    low = collectors.collect_disease(
        occurred_at=_dt(2026, 7, 1), disease="Spot", confidence=60,
        severity="low", crop="paddy", needs_expert=False, source_ref="r2",
    )
    assert low is not None and low.importance == Importance.MEDIUM.value


def test_collect_disease_none_without_disease():
    assert collectors.collect_disease(
        occurred_at=_dt(2026, 7, 1), disease=None, confidence=None,
        severity=None, crop=None, needs_expert=False, source_ref=None,
    ) is None


def test_collect_nutrient_possible_is_inferred_low():
    draft = collectors.collect_nutrient(
        occurred_at=_dt(2026, 7, 1), primary="nitrogen", status="possible",
        confidence=55, severity="mild", crop="paddy", needs_test=True, source_ref="n1",
    )
    assert draft is not None
    assert draft.importance == Importance.LOW.value
    assert draft.observation == "inferred"


def test_collect_nutrient_not_confirmed_dropped():
    assert collectors.collect_nutrient(
        occurred_at=_dt(2026, 7, 1), primary="nitrogen", status="not_confirmed",
        confidence=20, severity="unknown", crop="paddy", needs_test=True, source_ref="n2",
    ) is None


def test_collect_satellite_decline_vs_scan():
    decline = collectors.collect_satellite(
        occurred_at=_dt(2026, 7, 1), vegetation_health="low", trend="declining",
        stress_level="severe", declining=True, ndvi=0.2, crop="paddy", source_ref="s1",
    )
    assert decline.event_type == EventType.SATELLITE_VEGETATION_DECLINE.value
    assert decline.importance == Importance.HIGH.value
    assert decline.observation == "inferred"

    scan = collectors.collect_satellite(
        occurred_at=_dt(2026, 7, 1), vegetation_health="good", trend="stable",
        stress_level="none", declining=False, ndvi=0.8, crop="paddy", source_ref="s2",
    )
    assert scan.event_type == EventType.SATELLITE_SCAN.value
    assert scan.importance == Importance.LOW.value


def test_collect_weather_only_notable():
    assert collectors.collect_weather(
        occurred_at=_dt(2026, 7, 1), insight_codes=("field_work.ok",), crop="paddy",
    ) is None
    notable = collectors.collect_weather(
        occurred_at=_dt(2026, 7, 1),
        insight_codes=("heavy_rain.severe",), crop="paddy",
    )
    assert notable is not None and notable.importance == Importance.HIGH.value


# --------------------------------------------------------------------------- #
# Dedup + merge
# --------------------------------------------------------------------------- #
def test_dedup_key_stable_by_source_ref():
    d1 = collectors.collect_soil(
        occurred_at=_dt(2026, 7, 1), source="lab", confidence=95, crop="paddy", source_ref="rep1"
    )
    d2 = collectors.collect_soil(
        occurred_at=_dt(2026, 7, 1), source="lab", confidence=95, crop="paddy", source_ref="rep1"
    )
    assert d1.dedup_key() == d2.dedup_key()


def test_merge_collapses_duplicates_and_picks_lead():
    weak = collectors.collect_disease(
        occurred_at=_dt(2026, 7, 1), disease="Blast", confidence=50,
        severity="low", crop="paddy", needs_expert=False, source_ref="same",
    )
    strong = collectors.collect_disease(
        occurred_at=_dt(2026, 7, 1), disease="Blast", confidence=95,
        severity="high", crop="paddy", needs_expert=True, source_ref="same",
    )
    merged = merge_drafts([weak, strong])
    assert len(merged) == 1
    assert merged[0].occurrences == 2
    # The most important draft leads.
    assert merged[0].lead.importance == Importance.CRITICAL.value


def test_select_new_skips_existing_keys():
    d = collectors.collect_soil(
        occurred_at=_dt(2026, 7, 1), source="lab", confidence=95, crop="paddy", source_ref="rep1"
    )
    merged = merge_drafts([d])
    assert select_new(merged, set()) == merged
    assert select_new(merged, {merged[0].key}) == []


# --------------------------------------------------------------------------- #
# Summaries
# --------------------------------------------------------------------------- #
def _fact(  # noqa: ANN001
    key, module, event, importance, season, year="2026-season", crop="paddy", occ=None
):
    return MemoryFacts(
        key=key,
        source_module=module,
        event_type=event,
        importance=importance,
        season=season,
        season_year=year if isinstance(year, int) else 2026,
        crop=crop,
        occurred_at=occ or _dt(2026, 7, 1),
    )


def test_generate_summaries_groups_season_and_year():
    facts = [
        _fact("a", "disease", "disease_diagnosed", "critical", "kharif", 2026, occ=_dt(2026, 7, 1)),
        _fact("b", "soil", "soil_report_uploaded", "medium", "kharif", 2026, occ=_dt(2026, 8, 1)),
        _fact("c", "market", "market_price_viewed", "low", "rabi", 2026, occ=_dt(2026, 11, 1)),
    ]
    summaries = generate_summaries(facts, generated_at=_dt(2026, 12, 1))
    seasons = [s for s in summaries if s.period_type == "season"]
    years = [s for s in summaries if s.period_type == "year"]
    assert {s.period_key for s in seasons} == {"2026-kharif", "2026-rabi"}
    kharif = next(s for s in seasons if s.period_key == "2026-kharif")
    assert kharif.event_count == 2
    assert kharif.importance == "critical"  # top importance surfaced
    assert kharif.params["disease_count"] == 1
    assert years and years[0].period_key == "2026"
    assert years[0].event_count == 3


# --------------------------------------------------------------------------- #
# Links
# --------------------------------------------------------------------------- #
def test_link_follows_same_module():
    facts = [
        _fact("g1", "growth", "growth_tracked", "low", "kharif", occ=_dt(2026, 7, 1)),
        _fact("g2", "growth", "growth_tracked", "low", "kharif", occ=_dt(2026, 7, 8)),
    ]
    links = link_memories(facts)
    follows = [ln for ln in links if ln.link_type == LinkType.FOLLOWS.value]
    assert any(ln.from_key == "g2" and ln.to_key == "g1" for ln in follows)


def test_link_relates_cross_module_same_crop_season():
    facts = [
        _fact("d1", "disease", "disease_diagnosed", "high", "kharif", occ=_dt(2026, 7, 1)),
        _fact(
            "n1", "nutrient", "nutrient_deficiency_detected", "medium",
            "kharif", occ=_dt(2026, 7, 5),
        ),
    ]
    links = link_memories(facts)
    relates = [ln for ln in links if ln.link_type == LinkType.RELATES.value]
    assert any(ln.from_key == "n1" and ln.to_key == "d1" for ln in relates)


def test_link_resolves_expert_resolution_to_disease():
    facts = [
        _fact(
            "d1", "disease", EventType.DISEASE_DIAGNOSED.value, "high",
            "kharif", occ=_dt(2026, 7, 1),
        ),
        _fact(
            "e1", "experts", EventType.EXPERT_CONSULTATION_RESOLVED.value, "medium",
            "kharif", occ=_dt(2026, 7, 10),
        ),
    ]
    links = link_memories(facts)
    resolves = [ln for ln in links if ln.link_type == LinkType.RESOLVES.value]
    assert any(ln.from_key == "e1" and ln.to_key == "d1" for ln in resolves)


def test_link_ignored_when_no_source_module_overlap():
    # A single memory yields no links.
    facts = [_fact("only", "market", "market_price_viewed", "low", "kharif")]
    assert link_memories(facts) == []
