"""Unit tests for farmer schemas and pure helpers (no DB)."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from app.modules.farmers.schemas import (
    FarmerLanguageIn,
    FarmerMeOut,
    FarmerMeUpdate,
    LanguagesUpdate,
    PreferencesUpdate,
)
from app.modules.farmers.service import FarmerService
from pydantic import ValidationError


def test_full_name_min_length_enforced():
    with pytest.raises(ValidationError):
        FarmerMeUpdate(full_name="A")


def test_language_pattern_enforced():
    with pytest.raises(ValidationError):
        FarmerMeUpdate(full_name="Valid Name", language="fr")


def test_experience_bounds_enforced():
    with pytest.raises(ValidationError):
        FarmerMeUpdate(full_name="Valid Name", experience_years=200)


def test_preferences_reject_unknown_theme():
    with pytest.raises(ValidationError):
        PreferencesUpdate(theme="neon")


def test_preferences_partial_dump_omits_unset():
    payload = PreferencesUpdate(theme="dark")
    assert payload.model_dump(exclude_unset=True) == {"theme": "dark"}


def test_languages_update_requires_at_least_one():
    with pytest.raises(ValidationError):
        LanguagesUpdate(languages=[])


def test_normalise_languages_collapses_multiple_defaults():
    result = FarmerService._normalise_languages(
        [
            FarmerLanguageIn(language_code="ta", is_default=True),
            FarmerLanguageIn(language_code="en", is_default=True),
        ]
    )
    defaults = [i for i in result if i.is_default]
    assert len(defaults) == 1
    assert defaults[0].language_code == "ta"


def test_normalise_languages_dedupes_codes_and_sets_default():
    result = FarmerService._normalise_languages(
        [
            FarmerLanguageIn(language_code="ta"),
            FarmerLanguageIn(language_code="ta", is_default=True),
        ]
    )
    assert len(result) == 1
    assert result[0].language_code == "ta"
    assert result[0].is_default is True


def test_me_out_derives_preferred_crops_and_contact():
    now = datetime.now(UTC)
    profile = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        full_name="Vela Ram",
        gender=None,
        language="ta",
        district="madurai",
        block=None,
        village=None,
        profile_photo=None,
        experience_years=3,
        education=None,
        primary_crop="paddy",
        secondary_crop=None,
        created_at=now,
        updated_at=now,
    )
    user = SimpleNamespace(phone_number="+919999999999", email=None)

    out = FarmerMeOut.from_profile(profile, user)
    assert out.preferred_crops == ["paddy"]  # secondary is None → excluded
    assert out.phone_number == "+919999999999"
    assert out.email is None
