"""Unit tests for the deterministic eligibility engine (pure, no I/O)."""
from __future__ import annotations

from datetime import date

from app.modules.schemes.constants import (
    ANY,
    EligibilityStatus,
    FarmerCategory,
    SchemeStatus,
    derive_farmer_category,
)
from app.modules.schemes.engine import (
    EligibilityResult,
    FarmerContext,
    SchemeRules,
    evaluate,
    is_eligible,
    rank,
)


def _open_rules(**overrides) -> SchemeRules:
    """A scheme with no constraints, patched per-test."""
    return SchemeRules(**overrides)


# --------------------------------------------------------------------------- #
# derive_farmer_category
# --------------------------------------------------------------------------- #
def test_derive_farmer_category_bands() -> None:
    assert derive_farmer_category(0.5) is FarmerCategory.MARGINAL
    assert derive_farmer_category(1.0) is FarmerCategory.SMALL
    assert derive_farmer_category(1.9) is FarmerCategory.SMALL
    assert derive_farmer_category(2.0) is FarmerCategory.SEMI_MEDIUM
    assert derive_farmer_category(4.0) is FarmerCategory.MEDIUM
    assert derive_farmer_category(9.9) is FarmerCategory.MEDIUM
    assert derive_farmer_category(10.0) is FarmerCategory.LARGE
    assert derive_farmer_category(25.0) is FarmerCategory.LARGE


def test_derive_farmer_category_unknown() -> None:
    assert derive_farmer_category(None) is None
    assert derive_farmer_category(0) is None
    assert derive_farmer_category(-3) is None


# --------------------------------------------------------------------------- #
# Open scheme (no constraints) → always eligible
# --------------------------------------------------------------------------- #
def test_open_scheme_is_eligible_even_with_empty_context() -> None:
    result = evaluate(_open_rules(), FarmerContext())
    assert result.status == EligibilityStatus.ELIGIBLE.value
    assert result.unmet == []
    assert result.unknown == []
    assert 10 <= result.score <= 100


# --------------------------------------------------------------------------- #
# List constraints (state / district / crop / category)
# --------------------------------------------------------------------------- #
def test_matching_list_constraint_marks_eligible_and_matched() -> None:
    rules = _open_rules(states=["Tamil Nadu"])
    result = evaluate(rules, FarmerContext(state="Tamil Nadu"))
    assert result.status == EligibilityStatus.ELIGIBLE.value
    assert "state" in result.matched


def test_list_constraint_is_case_insensitive() -> None:
    rules = _open_rules(crops=["Paddy"])
    result = evaluate(rules, FarmerContext(crop="  paddy "))
    assert "crop" in result.matched
    assert result.status == EligibilityStatus.ELIGIBLE.value


def test_failing_list_constraint_makes_not_eligible() -> None:
    rules = _open_rules(states=["Kerala"])
    result = evaluate(rules, FarmerContext(state="Tamil Nadu"))
    assert result.status == EligibilityStatus.NOT_ELIGIBLE.value
    assert result.score == 0
    assert "state" in result.unmet


def test_missing_value_for_constrained_criterion_is_likely_eligible() -> None:
    rules = _open_rules(crops=["paddy"])
    result = evaluate(rules, FarmerContext(crop=None))
    assert result.status == EligibilityStatus.LIKELY.value
    assert "crop" in result.unknown
    assert is_eligible(result)


def test_explicit_all_sentinel_is_open() -> None:
    rules = _open_rules(states=[ANY], crops=[ANY])
    result = evaluate(rules, FarmerContext())
    assert result.matched == []
    assert result.status == EligibilityStatus.ELIGIBLE.value


# --------------------------------------------------------------------------- #
# Land constraints
# --------------------------------------------------------------------------- #
def test_land_within_bounds_matches() -> None:
    rules = _open_rules(min_land_hectares=1.0, max_land_hectares=4.0)
    result = evaluate(rules, FarmerContext(land_hectares=2.0))
    assert "land" in result.matched


def test_land_below_minimum_fails() -> None:
    rules = _open_rules(min_land_hectares=2.0)
    result = evaluate(rules, FarmerContext(land_hectares=1.0))
    assert result.status == EligibilityStatus.NOT_ELIGIBLE.value
    assert "land" in result.unmet


def test_land_above_maximum_fails() -> None:
    rules = _open_rules(max_land_hectares=4.0)
    result = evaluate(rules, FarmerContext(land_hectares=5.0))
    assert result.status == EligibilityStatus.NOT_ELIGIBLE.value
    assert "land" in result.unmet


def test_land_unknown_when_constrained_is_likely() -> None:
    rules = _open_rules(max_land_hectares=4.0)
    result = evaluate(rules, FarmerContext(land_hectares=None))
    assert result.status == EligibilityStatus.LIKELY.value
    assert "land" in result.unknown


# --------------------------------------------------------------------------- #
# Income constraints
# --------------------------------------------------------------------------- #
def test_income_at_or_below_ceiling_matches() -> None:
    rules = _open_rules(max_annual_income=200000)
    assert "income" in evaluate(rules, FarmerContext(annual_income=200000)).matched
    assert "income" in evaluate(rules, FarmerContext(annual_income=150000)).matched


def test_income_above_ceiling_fails() -> None:
    rules = _open_rules(max_annual_income=200000)
    result = evaluate(rules, FarmerContext(annual_income=300000))
    assert result.status == EligibilityStatus.NOT_ELIGIBLE.value
    assert "income" in result.unmet


# --------------------------------------------------------------------------- #
# Closed schemes
# --------------------------------------------------------------------------- #
def test_closed_scheme_is_never_eligible() -> None:
    rules = _open_rules(status=SchemeStatus.CLOSED.value)
    result = evaluate(rules, FarmerContext())
    assert result.status == EligibilityStatus.NOT_ELIGIBLE.value
    assert not is_eligible(result)


# --------------------------------------------------------------------------- #
# Application deadlines
# --------------------------------------------------------------------------- #
def test_scheme_past_its_deadline_is_never_eligible() -> None:
    rules = _open_rules(last_date=date(2026, 7, 31))
    result = evaluate(rules, FarmerContext(), today=date(2026, 8, 15))
    assert result.status == EligibilityStatus.NOT_ELIGIBLE.value
    assert "deadline" in result.unmet
    assert not is_eligible(result)


def test_scheme_before_its_deadline_or_with_no_today_stays_eligible() -> None:
    still_open = evaluate(
        _open_rules(last_date=date(2026, 12, 31)),
        FarmerContext(),
        today=date(2026, 8, 15),
    )
    assert still_open.status == EligibilityStatus.ELIGIBLE.value

    # No `today` passed → deadline check is skipped (caller not yet updated).
    no_today = evaluate(_open_rules(last_date=date(2026, 7, 31)), FarmerContext())
    assert no_today.status == EligibilityStatus.ELIGIBLE.value


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #
def test_more_matches_score_higher_than_open_scheme() -> None:
    targeted = evaluate(
        _open_rules(states=["Tamil Nadu"], crops=["paddy"]),
        FarmerContext(state="Tamil Nadu", crop="paddy"),
    )
    generic = evaluate(_open_rules(), FarmerContext(state="Tamil Nadu", crop="paddy"))
    assert targeted.score > generic.score


def test_unknowns_lower_the_score() -> None:
    known = evaluate(
        _open_rules(crops=["paddy"]), FarmerContext(crop="paddy")
    )
    unknown = evaluate(
        _open_rules(crops=["paddy"], max_annual_income=200000),
        FarmerContext(crop="paddy", annual_income=None),
    )
    assert unknown.score < known.score
    assert unknown.status == EligibilityStatus.LIKELY.value


def test_score_is_clamped_to_range() -> None:
    result = evaluate(_open_rules(), FarmerContext())
    assert 10 <= result.score <= 100


# --------------------------------------------------------------------------- #
# from_scheme adapter
# --------------------------------------------------------------------------- #
class _FakeScheme:
    states = ["Tamil Nadu"]
    districts = None
    crops = ["paddy"]
    farmer_categories = None
    min_land_hectares = None
    max_land_hectares = 4.0
    max_annual_income = None
    status = SchemeStatus.ACTIVE.value
    last_date = date(2026, 7, 31)


def test_rules_from_scheme_defaults_none_to_open() -> None:
    rules = SchemeRules.from_scheme(_FakeScheme())
    assert rules.states == ["Tamil Nadu"]
    assert rules.districts == [ANY]  # None → open
    assert rules.crops == ["paddy"]
    assert rules.max_land_hectares == 4.0


# --------------------------------------------------------------------------- #
# Ranking
# --------------------------------------------------------------------------- #
def _sr(status: str, score: int) -> EligibilityResult:
    return EligibilityResult(status=status, score=score)


class _RankScheme:
    def __init__(self, last_date: date | None) -> None:
        self.last_date = last_date


def test_rank_orders_eligible_before_likely() -> None:
    likely = (_RankScheme(None), _sr(EligibilityStatus.LIKELY.value, 90))
    eligible = (_RankScheme(None), _sr(EligibilityStatus.ELIGIBLE.value, 70))
    ordered = rank([likely, eligible])
    assert ordered[0] is eligible
    assert ordered[1] is likely


def test_rank_orders_higher_score_first_within_status() -> None:
    low = (_RankScheme(None), _sr(EligibilityStatus.ELIGIBLE.value, 60))
    high = (_RankScheme(None), _sr(EligibilityStatus.ELIGIBLE.value, 95))
    ordered = rank([low, high])
    assert ordered[0] is high


def test_rank_prefers_sooner_deadline_when_score_ties() -> None:
    soon = (_RankScheme(date(2026, 7, 20)), _sr(EligibilityStatus.ELIGIBLE.value, 80))
    later = (_RankScheme(date(2026, 12, 31)), _sr(EligibilityStatus.ELIGIBLE.value, 80))
    open_ended = (_RankScheme(None), _sr(EligibilityStatus.ELIGIBLE.value, 80))
    ordered = rank([open_ended, later, soon])
    assert ordered[0] is soon
    assert ordered[1] is later
    assert ordered[2] is open_ended
