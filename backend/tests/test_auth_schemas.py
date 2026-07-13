"""Validation tests for auth schemas (docs/API_CONTRACT.md)."""
from __future__ import annotations

import pytest
from app.modules.auth.schemas import (
    OtpSendRequest,
    ProfileUpdateRequest,
    SocialLoginRequest,
)
from pydantic import ValidationError


def test_profile_update_accepts_valid_payload() -> None:
    p = ProfileUpdateRequest(
        full_name="Muthu Kumar",
        language="ta",
        district="madurai",
        experience_years=12,
        preferred_crops=["paddy", "sugarcane"],
    )
    assert p.language == "ta"
    assert p.preferred_crops == ["paddy", "sugarcane"]


def test_profile_update_rejects_short_name() -> None:
    with pytest.raises(ValidationError):
        ProfileUpdateRequest(full_name="A")


def test_profile_update_rejects_bad_language() -> None:
    with pytest.raises(ValidationError):
        ProfileUpdateRequest(full_name="Muthu", language="fr")


def test_profile_update_rejects_out_of_range_experience() -> None:
    with pytest.raises(ValidationError):
        ProfileUpdateRequest(full_name="Muthu", experience_years=120)


def test_otp_send_requires_phone() -> None:
    assert OtpSendRequest(phone_number="+919876543210").phone_number
    with pytest.raises(ValidationError):
        OtpSendRequest(phone_number="123")


def test_social_login_requires_token() -> None:
    assert SocialLoginRequest(id_token="a-valid-looking-token").id_token
    with pytest.raises(ValidationError):
        SocialLoginRequest(id_token="short")
