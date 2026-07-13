"""Integration tests for the scheme service, provider seeding and bookmarks
(in-memory DB, mock provider)."""
from __future__ import annotations

import uuid

import pytest
from app.modules.auth.models import User
from app.modules.auth.profile_models import FarmerProfile
from app.modules.farms.models import Farm, FarmLocation
from app.modules.schemes.constants import (
    EligibilityStatus,
    FarmerCategory,
    SchemeTab,
)
from app.modules.schemes.exceptions import (
    BookmarkExistsError,
    BookmarkNotFoundError,
    SchemeNotFoundError,
)
from app.modules.schemes.provider import (
    MockSchemeProvider,
    ProviderDocument,
    ProviderScheme,
)
from app.modules.schemes.schemas import EligibilityQuery
from app.modules.schemes.service import SchemeService


async def _make_user(db_session, uid: str = "fb-scheme") -> User:
    user = User(firebase_uid=uid, status="active")
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_profile(db_session, user, **kwargs) -> FarmerProfile:
    profile = FarmerProfile(user_id=user.id, **kwargs)
    db_session.add(profile)
    await db_session.flush()
    return profile


async def _make_farm(db_session, user, *, district=None, **kwargs) -> Farm:
    farm = Farm(user_id=user.id, name=kwargs.pop("name", "Field A"), **kwargs)
    db_session.add(farm)
    await db_session.flush()
    if district is not None:
        farm.location = FarmLocation(farm_id=farm.id, district=district)
        await db_session.flush()
    return farm


def _service(db_session) -> SchemeService:
    return SchemeService(db_session, provider=MockSchemeProvider())


# --------------------------------------------------------------------------- #
# Seeding
# --------------------------------------------------------------------------- #
async def test_ensure_seeded_populates_verified_schemes_once(db_session) -> None:
    service = _service(db_session)
    await service.ensure_seeded()
    first = await service.repo.count()
    assert first > 0
    # Idempotent — a second call does not duplicate.
    await service.ensure_seeded()
    assert await service.repo.count() == first


async def test_seeded_schemes_have_documents_and_verified_at(db_session) -> None:
    service = _service(db_session)
    await service.ensure_seeded()
    pm_kisan = await service.repo.get_by_slug("pm-kisan")
    assert pm_kisan is not None
    assert pm_kisan.verified_at is not None
    assert pm_kisan.source == "mock"
    docs = await service.repo.documents_for(pm_kisan.id)
    assert len(docs) >= 1
    assert docs[0].display_order == 0


# --------------------------------------------------------------------------- #
# Listing
# --------------------------------------------------------------------------- #
async def test_list_all_paginates(db_session) -> None:
    user = await _make_user(db_session)
    service = _service(db_session)
    page = await service.list_all(
        user, category=None, state=None, crop=None, search=None, page=1, page_size=3
    )
    assert page.page_size == 3
    assert page.total > 3
    assert len(page.items) == 3
    assert page.total_pages >= 2


async def test_list_all_filters_by_category(db_session) -> None:
    user = await _make_user(db_session)
    service = _service(db_session)
    page = await service.list_all(
        user,
        category="insurance",
        state=None,
        crop=None,
        search=None,
        page=1,
        page_size=20,
    )
    assert page.total >= 1
    assert all(item.category == "insurance" for item in page.items)


async def test_list_all_search_matches_title(db_session) -> None:
    user = await _make_user(db_session)
    service = _service(db_session)
    page = await service.list_all(
        user, category=None, state=None, crop=None, search="kisan", page=1, page_size=20
    )
    assert page.total >= 1
    assert any("kisan" in item.title.lower() for item in page.items)


# --------------------------------------------------------------------------- #
# Eligibility engine driven
# --------------------------------------------------------------------------- #
async def test_eligible_marginal_tn_farmer_gets_targeted_schemes(db_session) -> None:
    user = await _make_user(db_session)
    await _make_profile(db_session, user, district="Thanjavur", primary_crop="paddy")
    service = _service(db_session)
    query = EligibilityQuery(
        state="Tamil Nadu",
        crop="black gram",
        land_hectares=1.5,
        annual_income=150000,
    )
    data, context = await service.eligible(user, query, page=1, page_size=50)
    slugs = {item.slug for item in data.items}
    # Open central schemes are always eligible.
    assert "pm-kisan" in slugs
    # The pulses scheme targets small pulse growers below the income ceiling.
    assert "nfsm-pulses" in slugs
    assert context.farmer_category == FarmerCategory.SMALL.value
    assert context.crop == "black gram"


async def test_eligible_excludes_failing_constraints(db_session) -> None:
    user = await _make_user(db_session)
    service = _service(db_session)
    # A large, high-income farmer growing an unrelated crop.
    query = EligibilityQuery(
        state="Tamil Nadu",
        crop="wheat",
        land_hectares=20.0,
        annual_income=900000,
    )
    data, _ = await service.eligible(user, query, page=1, page_size=50)
    slugs = {item.slug for item in data.items}
    # Pulses scheme requires small/marginal + low income → excluded.
    assert "nfsm-pulses" not in slugs
    # TN drip requires <= 4 ha → excluded for a 20 ha holding.
    assert "tn-drip-subsidy" not in slugs
    # Open income support is still eligible.
    assert "pm-kisan" in slugs


async def test_eligible_results_are_ranked_by_score(db_session) -> None:
    user = await _make_user(db_session)
    service = _service(db_session)
    query = EligibilityQuery(
        state="Tamil Nadu", crop="paddy", land_hectares=1.0, annual_income=100000
    )
    data, _ = await service.eligible(user, query, page=1, page_size=50)
    scores = [item.eligibility.score for item in data.items if item.eligibility]
    assert scores == sorted(scores, reverse=True)


async def test_state_specific_scheme_excluded_for_other_state(db_session) -> None:
    user = await _make_user(db_session)
    service = _service(db_session)
    query = EligibilityQuery(state="Kerala")
    data, _ = await service.eligible(user, query, page=1, page_size=50)
    slugs = {item.slug for item in data.items}
    assert "tn-free-electricity" not in slugs
    assert "pm-kisan" in slugs


async def test_context_defaults_to_tamil_nadu_and_derives_from_farm(db_session) -> None:
    user = await _make_user(db_session)
    await _make_profile(db_session, user, primary_crop="paddy")
    await _make_farm(
        db_session, user, district="Madurai", crop="cotton", area_hectares=3.0
    )
    service = _service(db_session)
    context = await service.build_context(user, EligibilityQuery())
    assert context.state == "Tamil Nadu"
    assert context.district == "Madurai"  # farm location wins
    assert context.land_hectares == 3.0
    assert context.farmer_category == FarmerCategory.SEMI_MEDIUM.value


async def test_farm_id_query_uses_that_farm(db_session) -> None:
    user = await _make_user(db_session)
    farm = await _make_farm(
        db_session, user, district="Erode", crop="banana", area_hectares=0.8
    )
    service = _service(db_session)
    context = await service.build_context(user, EligibilityQuery(farm_id=farm.id))
    assert context.district == "Erode"
    assert context.crop == "banana"
    assert context.farmer_category == FarmerCategory.MARGINAL.value


# --------------------------------------------------------------------------- #
# Recommended
# --------------------------------------------------------------------------- #
async def test_recommended_returns_minimum_set(db_session) -> None:
    user = await _make_user(db_session)
    service = _service(db_session)
    items, _ = await service.recommended(user, EligibilityQuery(state="Tamil Nadu"))
    assert len(items) >= 3
    # Recommended items are always eligible or likely-eligible.
    assert all(
        item.eligibility.status != EligibilityStatus.NOT_ELIGIBLE.value
        for item in items
        if item.eligibility
    )


# --------------------------------------------------------------------------- #
# Detail
# --------------------------------------------------------------------------- #
async def test_get_detail_includes_documents_steps_and_eligibility(db_session) -> None:
    user = await _make_user(db_session)
    service = _service(db_session)
    await service.ensure_seeded()
    scheme = await service.repo.get_by_slug("pmfby")
    detail = await service.get_detail(user, scheme.id)
    assert detail.slug == "pmfby"
    assert detail.documents
    assert detail.application_steps
    assert detail.eligibility is not None
    assert detail.verified_at is not None


async def test_get_detail_unknown_scheme_raises(db_session) -> None:
    user = await _make_user(db_session)
    service = _service(db_session)
    await service.ensure_seeded()
    with pytest.raises(SchemeNotFoundError):
        await service.get_detail(user, uuid.uuid4())


# --------------------------------------------------------------------------- #
# Bookmarks
# --------------------------------------------------------------------------- #
async def test_bookmark_add_list_and_prevent_duplicates(db_session) -> None:
    user = await _make_user(db_session)
    service = _service(db_session)
    await service.ensure_seeded()
    scheme = await service.repo.get_by_slug("kcc")

    await service.add_bookmark(user, scheme.id)
    bookmarks = await service.list_bookmarks(user)
    assert len(bookmarks) == 1
    assert bookmarks[0].slug == "kcc"
    assert bookmarks[0].bookmarked is True
    assert bookmarks[0].eligibility is not None

    with pytest.raises(BookmarkExistsError):
        await service.add_bookmark(user, scheme.id)


async def test_bookmark_add_unknown_scheme_raises(db_session) -> None:
    user = await _make_user(db_session)
    service = _service(db_session)
    await service.ensure_seeded()
    with pytest.raises(SchemeNotFoundError):
        await service.add_bookmark(user, uuid.uuid4())


async def test_bookmark_remove_and_ownership(db_session) -> None:
    owner = await _make_user(db_session, uid="fb-owner")
    other = await _make_user(db_session, uid="fb-other")
    service = _service(db_session)
    await service.ensure_seeded()
    scheme = await service.repo.get_by_slug("kcc")

    await service.add_bookmark(owner, scheme.id)
    # Another user has not bookmarked it → cannot remove.
    with pytest.raises(BookmarkNotFoundError):
        await service.remove_bookmark(other, scheme.id)

    await service.remove_bookmark(owner, scheme.id)
    assert await service.list_bookmarks(owner) == []
    # Removing again fails.
    with pytest.raises(BookmarkNotFoundError):
        await service.remove_bookmark(owner, scheme.id)


async def test_bookmarked_flag_reflected_in_listings(db_session) -> None:
    user = await _make_user(db_session)
    service = _service(db_session)
    await service.ensure_seeded()
    scheme = await service.repo.get_by_slug("pm-kisan")
    await service.add_bookmark(user, scheme.id)
    page = await service.list_all(
        user, category=None, state=None, crop=None, search=None, page=1, page_size=50
    )
    marked = next(i for i in page.items if i.slug == "pm-kisan")
    assert marked.bookmarked is True


# --------------------------------------------------------------------------- #
# Provider abstraction
# --------------------------------------------------------------------------- #
async def test_custom_provider_is_used_for_seeding(db_session) -> None:
    custom = MockSchemeProvider(
        schemes=[
            ProviderScheme(
                slug="test-scheme",
                title="Test Only Scheme",
                category="subsidy",
                description="A single verified test scheme.",
                benefits="Benefit.",
                eligibility_summary="Everyone.",
                application_steps=["Apply."],
                departments=["Dept"],
                official_url="https://example.gov.in",
                documents=[ProviderDocument("Aadhaar card")],
                source="mock",
            )
        ]
    )
    service = SchemeService(db_session, provider=custom)
    await service.ensure_seeded()
    assert await service.repo.count() == 1
    only = await service.repo.get_by_slug("test-scheme")
    assert only is not None
    assert only.title == "Test Only Scheme"


def test_scheme_tab_values() -> None:
    assert {t.value for t in SchemeTab} == {
        "eligible",
        "recommended",
        "all",
        "bookmarked",
    }
