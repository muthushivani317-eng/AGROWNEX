"""Tests for the hand-curated real-scheme provider (2026-08 pre-release audit
follow-up: schemes previously had no real data source outside dev/test mock
mode; app.modules.schemes.curated_data.CURATED_SCHEMES replaces that gap with
individually-sourced, dated real government scheme content -- see that
module's docstring for why this is not a live API)."""
from __future__ import annotations

import asyncio
from datetime import date, timedelta

import pytest
from app.modules.schemes import provider as provider_module
from app.modules.schemes.curated_data import (
    CURATED_SCHEMES,
    LAST_VERIFIED_DATE,
    LAST_VERIFIED_STALE_AFTER_DAYS,
    SCHEME_SOURCES,
    is_curated_data_stale,
)
from app.modules.schemes.provider import (
    CuratedSchemeProvider,
    MockSchemeProvider,
    UnavailableSchemeProvider,
    get_default_provider,
)


# --------------------------------------------------------------------------- #
# Content integrity -- every curated scheme is a real, sourced, complete record
# --------------------------------------------------------------------------- #
def test_curated_schemes_slugs_are_unique() -> None:
    slugs = [s.slug for s in CURATED_SCHEMES]
    assert len(slugs) == len(set(slugs))
    assert len(slugs) >= 10


@pytest.mark.parametrize("scheme", CURATED_SCHEMES, ids=lambda s: s.slug)
def test_every_curated_scheme_is_complete_and_officially_sourced(scheme) -> None:
    assert scheme.title.strip()
    assert scheme.description.strip()
    assert scheme.benefits.strip()
    assert scheme.eligibility_summary.strip()
    assert scheme.application_steps, f"{scheme.slug} has no application steps"
    assert scheme.documents, f"{scheme.slug} lists no required documents"
    assert scheme.departments, f"{scheme.slug} lists no owning department"
    # Every scheme must point at a real government (.gov.in) domain -- never a
    # blog, aggregator or unverified third-party page (docs/PRODUCT_RULES.md
    # rule 4: only verified schemes, from verified sources).
    assert scheme.official_url.startswith("https://")
    assert ".gov.in" in scheme.official_url


def test_curated_schemes_never_claim_a_guessed_deadline() -> None:
    """Regression guard: the old mock data hard-coded PMFBY's `last_date` to a
    fixed date that had already passed by the time anyone looked at it again
    (2026-07-31, seeded well before this file was written on 2026-08-16). The
    real PMFBY/RWBCIS enrollment window is seasonal and state-specific, so
    curated_data.py deliberately leaves `last_date=None` for both rather than
    guess a date that will silently go stale."""
    by_slug = {s.slug: s for s in CURATED_SCHEMES}
    assert by_slug["pmfby"].last_date is None
    assert by_slug["rwbcis"].last_date is None


def test_scheme_sources_citation_registry_has_no_fabricated_dates() -> None:
    """Every citation either states the real date the source document itself
    carried, or None -- never a guessed date (mirrors the discipline in
    app/disease_recommendations/registry.py's OFFICIAL_SOURCES)."""
    for source in SCHEME_SOURCES:
        assert source["url"].startswith("https://")
        assert source["official"] is True
        if source["source_date"] is not None:
            # Must parse as a real ISO date, not a placeholder string.
            date.fromisoformat(source["source_date"])


# --------------------------------------------------------------------------- #
# Staleness gate
# --------------------------------------------------------------------------- #
def test_is_curated_data_stale_boundary() -> None:
    verified = date.fromisoformat(LAST_VERIFIED_DATE)
    assert is_curated_data_stale(as_of=verified) is False
    assert (
        is_curated_data_stale(
            as_of=verified + timedelta(days=LAST_VERIFIED_STALE_AFTER_DAYS)
        )
        is False
    )
    assert (
        is_curated_data_stale(
            as_of=verified + timedelta(days=LAST_VERIFIED_STALE_AFTER_DAYS + 1)
        )
        is True
    )


# --------------------------------------------------------------------------- #
# get_default_provider() selection logic
# --------------------------------------------------------------------------- #
def test_default_provider_is_curated_outside_test_mock_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGROWAI_ENABLE_TEST_MOCKS", raising=False)
    monkeypatch.setenv("APP_ENV", "production")

    provider = get_default_provider()

    assert isinstance(provider, CuratedSchemeProvider)
    assert not isinstance(provider, MockSchemeProvider)
    schemes = asyncio.run(provider.fetch_schemes())
    assert len(schemes) == len(CURATED_SCHEMES)


def test_default_provider_is_mock_only_with_explicit_test_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AGROWAI_ENABLE_TEST_MOCKS", "true")

    assert isinstance(get_default_provider(), MockSchemeProvider)


def test_default_provider_fails_closed_when_curated_data_is_stale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGROWAI_ENABLE_TEST_MOCKS", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setattr(provider_module, "is_curated_data_stale", lambda: True)

    provider = get_default_provider()

    assert isinstance(provider, UnavailableSchemeProvider)
    with pytest.raises(Exception):
        asyncio.run(provider.fetch_schemes())
