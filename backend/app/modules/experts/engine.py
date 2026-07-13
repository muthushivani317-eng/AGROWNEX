"""Expert Engine (docs: Repository → Service → Expert Engine → Provider).

Pure, deterministic and fully unit-tested. Given a consultation's context and a
pool of verified expert desks it computes a transparent match score and assigns
the best desk — plus the consultation status-transition rules. No AI, no I/O, no
side effects (AI-assisted assignment/replies are future-ready behind the same
seam). Every decision is explainable.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.experts.constants import (
    FARMER_SETTABLE_STATUSES,
    SCORE_AVAILABLE,
    SCORE_CATEGORY_MATCH,
    SCORE_CROP_MATCH,
    SCORE_DISTRICT_MATCH,
    SCORE_GENERALIST,
    SCORE_LANGUAGE_MATCH,
    SCORE_LOAD_PENALTY,
    SCORE_VERIFIED,
    TERMINAL_STATUSES,
    ConsultationCategory,
    ConsultationStatus,
)


@dataclass(frozen=True)
class ExpertCandidate:
    """The subset of a verified expert desk the engine reasons about (pure)."""

    id: str
    categories: frozenset[str]
    crops: frozenset[str] = field(default_factory=frozenset)
    districts: frozenset[str] = field(default_factory=frozenset)
    languages: frozenset[str] = field(default_factory=frozenset)
    verified: bool = True
    is_available: bool = True
    is_generalist: bool = False
    rating: float | None = None
    active_load: int = 0  # currently-open consultations already assigned to this desk


@dataclass(frozen=True)
class ConsultationContext:
    """The pure inputs the engine matches against."""

    category: str
    crop: str | None = None
    district: str | None = None
    language: str | None = None


@dataclass(frozen=True)
class AssignmentResult:
    expert_id: str | None
    score: int
    reasons: tuple[str, ...]


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


def score_expert(
    candidate: ExpertCandidate, context: ConsultationContext
) -> tuple[int, tuple[str, ...]]:
    """Transparent 0+ score for one desk against a consultation (pure)."""
    score = 0
    reasons: list[str] = []
    category = _norm(context.category)

    if category in {_norm(c) for c in candidate.categories}:
        score += SCORE_CATEGORY_MATCH
        reasons.append("category_match")
    elif candidate.is_generalist or _norm(ConsultationCategory.GENERAL.value) in {
        _norm(c) for c in candidate.categories
    }:
        score += SCORE_GENERALIST
        reasons.append("generalist")

    if context.crop and _norm(context.crop) in {_norm(c) for c in candidate.crops}:
        score += SCORE_CROP_MATCH
        reasons.append("crop_match")

    if context.district and _norm(context.district) in {
        _norm(d) for d in candidate.districts
    }:
        score += SCORE_DISTRICT_MATCH
        reasons.append("district_match")

    if context.language and _norm(context.language) in {
        _norm(lang) for lang in candidate.languages
    }:
        score += SCORE_LANGUAGE_MATCH
        reasons.append("language_match")

    if candidate.verified:
        score += SCORE_VERIFIED
        reasons.append("verified")

    if candidate.is_available:
        score += SCORE_AVAILABLE
        reasons.append("available")

    score -= SCORE_LOAD_PENALTY * max(0, candidate.active_load)

    return score, tuple(reasons)


def assign_expert(
    candidates: list[ExpertCandidate], context: ConsultationContext
) -> AssignmentResult:
    """Pick the best-matching desk deterministically.

    Ranking: highest score, then (stable tie-break) lowest expert id. Returns a
    null assignment when there is no eligible desk — never fabricates one.
    """
    scored = [
        (score, reasons, candidate)
        for candidate in candidates
        for score, reasons in [score_expert(candidate, context)]
        if candidate.verified and candidate.is_available
    ]
    if not scored:
        return AssignmentResult(expert_id=None, score=0, reasons=())

    scored.sort(key=lambda item: (-item[0], item[2].id))
    best_score, best_reasons, best = scored[0]
    return AssignmentResult(expert_id=best.id, score=best_score, reasons=best_reasons)


# --------------------------------------------------------------------------- #
# Status-transition rules (pure)
# --------------------------------------------------------------------------- #
_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    ConsultationStatus.SUBMITTED.value: frozenset(
        {
            ConsultationStatus.ASSIGNED.value,
            ConsultationStatus.IN_PROGRESS.value,
            ConsultationStatus.CANCELLED.value,
        }
    ),
    ConsultationStatus.ASSIGNED.value: frozenset(
        {
            ConsultationStatus.IN_PROGRESS.value,
            ConsultationStatus.AWAITING_FARMER.value,
            ConsultationStatus.AWAITING_EXPERT.value,
            ConsultationStatus.RESOLVED.value,
            ConsultationStatus.CANCELLED.value,
        }
    ),
    ConsultationStatus.IN_PROGRESS.value: frozenset(
        {
            ConsultationStatus.AWAITING_FARMER.value,
            ConsultationStatus.AWAITING_EXPERT.value,
            ConsultationStatus.RESOLVED.value,
            ConsultationStatus.CANCELLED.value,
        }
    ),
    ConsultationStatus.AWAITING_FARMER.value: frozenset(
        {
            ConsultationStatus.AWAITING_EXPERT.value,
            ConsultationStatus.IN_PROGRESS.value,
            ConsultationStatus.RESOLVED.value,
            ConsultationStatus.CANCELLED.value,
        }
    ),
    ConsultationStatus.AWAITING_EXPERT.value: frozenset(
        {
            ConsultationStatus.IN_PROGRESS.value,
            ConsultationStatus.AWAITING_FARMER.value,
            ConsultationStatus.RESOLVED.value,
            ConsultationStatus.CANCELLED.value,
        }
    ),
    ConsultationStatus.RESOLVED.value: frozenset(
        {ConsultationStatus.CLOSED.value, ConsultationStatus.IN_PROGRESS.value}
    ),
}


def can_transition(old: str, new: str) -> bool:
    """True when ``old → new`` is a permitted status change (pure)."""
    if old == new:
        return False
    if old in TERMINAL_STATUSES and old != ConsultationStatus.RESOLVED.value:
        return False
    return new in _ALLOWED_TRANSITIONS.get(old, frozenset())


def farmer_can_set(new: str) -> bool:
    """True when a farmer is allowed to request this status directly."""
    return new in FARMER_SETTABLE_STATUSES
