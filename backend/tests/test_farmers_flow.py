"""Integration tests for the Farmer Profile service (docs/API_CONTRACT.md → FARMER).

Runs against the in-memory DB from conftest, exercising the real repositories:
profile upsert, preference partial update, and language-set replacement.
"""
from __future__ import annotations

import pytest
from app.modules.auth.exceptions import ProfileNotFoundError
from app.modules.auth.models import User
from app.modules.farmers.schemas import (
    FarmerLanguageIn,
    FarmerMeUpdate,
    LanguagesUpdate,
    PreferencesUpdate,
)
from app.modules.farmers.service import FarmerService


async def _make_user(db_session, uid: str = "fb-farmer-1") -> User:
    user = User(
        firebase_uid=uid,
        phone_number="+919876500000",
        email=None,
        is_phone_verified=True,
        is_email_verified=False,
        status="active",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def test_get_me_requires_profile(db_session):
    service = FarmerService(db_session)
    user = await _make_user(db_session)
    with pytest.raises(ProfileNotFoundError):
        await service.get_me(user)


async def test_update_me_creates_profile_and_defaults(db_session):
    service = FarmerService(db_session)
    user = await _make_user(db_session)

    profile = await service.update_me(
        user,
        FarmerMeUpdate(
            full_name="Selvi Murugan",
            language="ta",
            district="thanjavur",
            block="Orathanadu",
            village="Pillaiyarpatti",
            experience_years=9,
            preferred_crops=["paddy", "banana", "coconut"],
        ),
    )
    # Only the first two crops persist (primary/secondary columns).
    assert profile.primary_crop == "paddy"
    assert profile.secondary_crop == "banana"

    # Preference + default language rows are created on first save.
    pref = await service.get_preferences(user)
    assert pref.theme == "system"
    assert pref.default_crop == "paddy"

    langs = await service.get_languages(user)
    assert len(langs) == 1
    assert langs[0].language_code == "ta"
    assert langs[0].is_default is True

    fetched = await service.get_me(user)
    assert fetched.id == profile.id
    assert fetched.full_name == "Selvi Murugan"


async def test_update_me_is_idempotent_single_row(db_session):
    service = FarmerService(db_session)
    user = await _make_user(db_session)

    first = await service.update_me(
        user, FarmerMeUpdate(full_name="Muthu Kumar", preferred_crops=["cotton"])
    )
    second = await service.update_me(
        user, FarmerMeUpdate(full_name="Muthu K", language="en", preferred_crops=[])
    )
    assert first.id == second.id  # same row, no duplicate
    assert second.full_name == "Muthu K"
    assert second.language == "en"
    assert second.primary_crop is None


async def test_update_preferences_is_partial(db_session):
    service = FarmerService(db_session)
    user = await _make_user(db_session)
    await service.update_me(
        user, FarmerMeUpdate(full_name="Raj Kumar", preferred_crops=["cotton"])
    )

    updated = await service.update_preferences(
        user,
        PreferencesUpdate(notifications_enabled=False, preferred_units="imperial"),
    )
    assert updated.notifications_enabled is False
    assert updated.preferred_units == "imperial"
    assert updated.voice_enabled is True  # untouched default
    assert updated.theme == "system"  # untouched default


async def test_update_languages_replaces_and_syncs_profile(db_session):
    service = FarmerService(db_session)
    user = await _make_user(db_session)
    await service.update_me(
        user, FarmerMeUpdate(full_name="Kumar S", language="ta", preferred_crops=[])
    )

    rows = await service.update_languages(
        user,
        LanguagesUpdate(
            languages=[
                FarmerLanguageIn(language_code="ta", is_default=False),
                FarmerLanguageIn(language_code="en", is_default=True),
            ]
        ),
    )
    by_code = {r.language_code: r.is_default for r in rows}
    assert by_code == {"ta": False, "en": True}

    # The profile's primary language follows the default choice.
    profile = await service.get_me(user)
    assert profile.language == "en"

    # A second replacement does not accumulate rows.
    rows2 = await service.update_languages(
        user,
        LanguagesUpdate(languages=[FarmerLanguageIn(language_code="ta", is_default=True)]),
    )
    assert len(rows2) == 1
    assert rows2[0].language_code == "ta"
    assert rows2[0].is_default is True


async def test_update_languages_forces_exactly_one_default(db_session):
    service = FarmerService(db_session)
    user = await _make_user(db_session)
    await service.update_me(
        user, FarmerMeUpdate(full_name="Anitha R", preferred_crops=[])
    )

    # No default supplied → the first entry becomes the default.
    rows = await service.update_languages(
        user,
        LanguagesUpdate(
            languages=[
                FarmerLanguageIn(language_code="ta"),
                FarmerLanguageIn(language_code="en"),
            ]
        ),
    )
    defaults = [r for r in rows if r.is_default]
    assert len(defaults) == 1
    assert defaults[0].language_code == "ta"
