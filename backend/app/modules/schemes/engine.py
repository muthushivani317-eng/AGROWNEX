"""Eligibility Engine (docs: Repository → Service → Eligibility Engine → Provider).

Pure, deterministic and fully unit-tested. Given a farmer's context it evaluates
each scheme's structured rules, classifies eligibility, assigns a transparent
0-100 relevance score and ranks the results. No AI, no side effects, no I/O —
so recommendations are explainable and reproducible.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.schemes.constants import (
    ANY,
    EligibilityStatus,
    FarmerCategory,
    SchemeStatus,
)

# Per-criterion evaluation outcomes.
_OPEN = "open"  # the scheme places no constraint on this criterion
_MATCH = "match"  # the farmer's known value satisfies the constraint
_FAIL = "fail"  # the farmer's known value violates the constraint
_UNKNOWN = "unknown"  # the scheme constrains it, but the farmer's value is missing

_CRITERIA = ("state", "district", "crop", "category", "land", "income")


@dataclass(frozen=True)
class FarmerContext:
    """Everything the engine needs about the farmer (from profile + farm)."""

    state: str | None = None
    district: str | None = None
    crop: str | None = None
    land_hectares: float | None = None
    annual_income: int | None = None
    farmer_category: FarmerCategory | None = None


@dataclass(frozen=True)
class SchemeRules:
    """The machine-evaluable rules extracted from a scheme."""

    states: list[str] = field(default_factory=lambda: [ANY])
    districts: list[str] = field(default_factory=lambda: [ANY])
    crops: list[str] = field(default_factory=lambda: [ANY])
    farmer_categories: list[str] = field(default_factory=lambda: [ANY])
    min_land_hectares: float | None = None
    max_land_hectares: float | None = None
    max_annual_income: int | None = None
    status: str = SchemeStatus.ACTIVE.value

    @classmethod
    def from_scheme(cls, scheme: object) -> SchemeRules:
        """Build from an ORM scheme (or any object with matching attributes)."""
        return cls(
            states=list(getattr(scheme, "states", None) or [ANY]),
            districts=list(getattr(scheme, "districts", None) or [ANY]),
            crops=list(getattr(scheme, "crops", None) or [ANY]),
            farmer_categories=list(getattr(scheme, "farmer_categories", None) or [ANY]),
            min_land_hectares=getattr(scheme, "min_land_hectares", None),
            max_land_hectares=getattr(scheme, "max_land_hectares", None),
            max_annual_income=getattr(scheme, "max_annual_income", None),
            status=getattr(scheme, "status", SchemeStatus.ACTIVE.value),
        )


@dataclass
class EligibilityResult:
    status: str
    score: int
    matched: list[str] = field(default_factory=list)
    unmet: list[str] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)


def _norm(value: str) -> str:
    return value.strip().lower()


def _list_outcome(allowed: list[str] | None, value: str | None) -> str:
    if not allowed or any(_norm(a) == ANY for a in allowed):
        return _OPEN
    if value is None or not str(value).strip():
        return _UNKNOWN
    return _MATCH if _norm(str(value)) in {_norm(a) for a in allowed} else _FAIL


def _land_outcome(
    min_land: float | None, max_land: float | None, land: float | None
) -> str:
    if min_land is None and max_land is None:
        return _OPEN
    if land is None:
        return _UNKNOWN
    if min_land is not None and land < min_land:
        return _FAIL
    if max_land is not None and land > max_land:
        return _FAIL
    return _MATCH


def _income_outcome(max_income: int | None, income: int | None) -> str:
    if max_income is None:
        return _OPEN
    if income is None:
        return _UNKNOWN
    return _MATCH if income <= max_income else _FAIL


def _score(matched: list[str], unknown: list[str]) -> int:
    """Transparent 0-100 score: targeted matches raise it, unknowns lower it."""
    score = 55 + 12 * len(matched) - 8 * len(unknown)
    return max(10, min(100, score))


def evaluate(rules: SchemeRules, context: FarmerContext) -> EligibilityResult:
    """Classify a single scheme for a farmer (pure)."""
    category_value = (
        context.farmer_category.value if context.farmer_category else None
    )
    outcomes = {
        "state": _list_outcome(rules.states, context.state),
        "district": _list_outcome(rules.districts, context.district),
        "crop": _list_outcome(rules.crops, context.crop),
        "category": _list_outcome(rules.farmer_categories, category_value),
        "land": _land_outcome(
            rules.min_land_hectares, rules.max_land_hectares, context.land_hectares
        ),
        "income": _income_outcome(rules.max_annual_income, context.annual_income),
    }
    matched = [c for c in _CRITERIA if outcomes[c] == _MATCH]
    unmet = [c for c in _CRITERIA if outcomes[c] == _FAIL]
    unknown = [c for c in _CRITERIA if outcomes[c] == _UNKNOWN]

    if rules.status == SchemeStatus.CLOSED.value or unmet:
        return EligibilityResult(
            status=EligibilityStatus.NOT_ELIGIBLE.value,
            score=0,
            matched=matched,
            unmet=unmet,
            unknown=unknown,
        )

    status = (
        EligibilityStatus.LIKELY.value
        if unknown
        else EligibilityStatus.ELIGIBLE.value
    )
    return EligibilityResult(
        status=status,
        score=_score(matched, unknown),
        matched=matched,
        unmet=unmet,
        unknown=unknown,
    )


_STATUS_ORDER = {
    EligibilityStatus.ELIGIBLE.value: 0,
    EligibilityStatus.LIKELY.value: 1,
    EligibilityStatus.NOT_ELIGIBLE.value: 2,
}


def is_eligible(result: EligibilityResult) -> bool:
    """Eligible (certain) or likely-eligible (pending some farmer data)."""
    return result.status != EligibilityStatus.NOT_ELIGIBLE.value


def rank_key(item: tuple[object, EligibilityResult]) -> tuple:
    """Sort: eligible first, then higher score, then closing soonest."""
    scheme, result = item
    last = getattr(scheme, "last_date", None)
    # Schemes with a deadline sort before open-ended ones; sooner deadlines first.
    deadline_key = (0, last.toordinal()) if last is not None else (1, 0)
    return (_STATUS_ORDER.get(result.status, 3), -result.score, *deadline_key)


def rank(
    items: list[tuple[object, EligibilityResult]],
) -> list[tuple[object, EligibilityResult]]:
    return sorted(items, key=rank_key)
