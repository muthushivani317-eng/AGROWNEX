"""Unit tests for the pure Expert Engine: deterministic assignment scoring, the
generalist fallback, status-transition rules, and the notifications collector
(no database)."""
from __future__ import annotations

from app.modules.experts.constants import ConsultationStatus
from app.modules.experts.engine import (
    ConsultationContext,
    ExpertCandidate,
    assign_expert,
    can_transition,
    farmer_can_set,
    score_expert,
)
from app.modules.notifications.collectors import (
    ExpertConsultationView,
    collect_experts,
)


def _candidate(cid: str, **kwargs) -> ExpertCandidate:
    base = dict(
        id=cid,
        categories=frozenset({"crop_disease"}),
        crops=frozenset(),
        districts=frozenset(),
        languages=frozenset({"ta"}),
        verified=True,
        is_available=True,
        is_generalist=False,
    )
    base.update(kwargs)
    return ExpertCandidate(**base)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #
def test_category_match_scores_highest() -> None:
    ctx = ConsultationContext(category="crop_disease", district="Thanjavur", language="ta")
    match = _candidate("a")
    other = _candidate("b", categories=frozenset({"market"}))
    match_score, reasons = score_expert(match, ctx)
    other_score, _ = score_expert(other, ctx)
    assert match_score > other_score
    assert "category_match" in reasons


def test_crop_district_language_add_score() -> None:
    ctx = ConsultationContext(
        category="crop_disease", crop="Paddy", district="Thanjavur", language="ta"
    )
    rich = _candidate(
        "a",
        crops=frozenset({"paddy"}),
        districts=frozenset({"thanjavur"}),
        languages=frozenset({"ta"}),
    )
    bare = _candidate("b", districts=frozenset({"salem"}), languages=frozenset({"en"}))
    assert score_expert(rich, ctx)[0] > score_expert(bare, ctx)[0]


def test_generalist_fallback_when_no_category_match() -> None:
    ctx = ConsultationContext(category="market", district=None, language="ta")
    generalist = _candidate(
        "gen", categories=frozenset({"general"}), is_generalist=True
    )
    score, reasons = score_expert(generalist, ctx)
    assert "generalist" in reasons
    assert score > 0


def test_load_penalty_reduces_score() -> None:
    ctx = ConsultationContext(category="crop_disease")
    idle = _candidate("a", active_load=0)
    busy = _candidate("b", active_load=5)
    assert score_expert(idle, ctx)[0] > score_expert(busy, ctx)[0]


# --------------------------------------------------------------------------- #
# Assignment
# --------------------------------------------------------------------------- #
def test_assign_picks_best_and_is_deterministic() -> None:
    ctx = ConsultationContext(category="crop_disease", district="Thanjavur")
    best = _candidate("z-best", districts=frozenset({"thanjavur"}))
    ok = _candidate("a-ok")
    result = assign_expert([ok, best], ctx)
    assert result.expert_id == "z-best"


def test_assign_tie_break_by_id() -> None:
    ctx = ConsultationContext(category="crop_disease")
    a = _candidate("a")
    b = _candidate("b")
    # Identical scores → deterministic lowest-id winner.
    assert assign_expert([b, a], ctx).expert_id == "a"


def test_assign_skips_unverified_and_unavailable() -> None:
    ctx = ConsultationContext(category="crop_disease")
    unverified = _candidate("a", verified=False)
    away = _candidate("b", is_available=False)
    good = _candidate("c")
    assert assign_expert([unverified, away, good], ctx).expert_id == "c"


def test_assign_returns_none_when_no_candidates() -> None:
    ctx = ConsultationContext(category="crop_disease")
    assert assign_expert([], ctx).expert_id is None


# --------------------------------------------------------------------------- #
# Status transitions
# --------------------------------------------------------------------------- #
def test_valid_and_invalid_transitions() -> None:
    cs = ConsultationStatus
    assert can_transition(cs.SUBMITTED.value, cs.ASSIGNED.value)
    assert can_transition(cs.ASSIGNED.value, cs.RESOLVED.value)
    assert can_transition(cs.RESOLVED.value, cs.CLOSED.value)
    assert not can_transition(cs.CANCELLED.value, cs.ASSIGNED.value)  # terminal
    assert not can_transition(cs.CLOSED.value, cs.IN_PROGRESS.value)  # terminal
    assert not can_transition(cs.ASSIGNED.value, cs.ASSIGNED.value)   # no-op


def test_farmer_settable_statuses() -> None:
    assert farmer_can_set(ConsultationStatus.RESOLVED.value)
    assert farmer_can_set(ConsultationStatus.CANCELLED.value)
    assert not farmer_can_set(ConsultationStatus.ASSIGNED.value)
    assert not farmer_can_set(ConsultationStatus.IN_PROGRESS.value)


# --------------------------------------------------------------------------- #
# Notifications collector
# --------------------------------------------------------------------------- #
def test_collect_experts_emits_assignment() -> None:
    events = collect_experts(
        ExpertConsultationView(
            consultation_id="c1", subject="Leaf spots", assigned=True,
            expert_name="TNAU Plant Health Clinic",
        )
    )
    types = {e.event_type for e in events}
    assert types == {"consultation_assigned"}


def test_collect_experts_emits_reply_and_resolved() -> None:
    events = collect_experts(
        ExpertConsultationView(
            consultation_id="c1", subject="Leaf spots", assigned=True,
            expert_name="Desk", latest_expert_message_id="m9", resolved_by_expert=True,
        )
    )
    types = {e.event_type for e in events}
    assert types == {
        "consultation_assigned", "consultation_reply", "consultation_resolved"
    }


def test_collect_experts_unassigned_is_silent() -> None:
    assert collect_experts(
        ExpertConsultationView(consultation_id="c1", subject="x", assigned=False)
    ) == []
