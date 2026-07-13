"""Integration tests for the auth service (docs/API_CONTRACT.md, SECURITY.md).

Runs against an in-memory DB with Firebase verification stubbed, exercising the
real repositories, session establishment, refresh rotation and profile setup.
"""
from __future__ import annotations

import pytest
from app.modules.auth import service as service_module
from app.modules.auth.exceptions import (
    InvalidRefreshTokenError,
    OtpRateLimitError,
    ProfileNotFoundError,
)
from app.modules.auth.schemas import ProfileUpdateRequest
from app.modules.auth.service import AuthService

FAKE_CLAIMS = {
    "uid": "firebase-uid-123",
    "phone_number": "+919876543210",
    "email": None,
    "email_verified": False,
}


@pytest.fixture(autouse=True)
def _stub_firebase(monkeypatch):
    """Bypass real Firebase verification; return fixed claims."""
    monkeypatch.setattr(service_module, "verify_id_token", lambda _token: FAKE_CLAIMS)


async def test_send_otp_then_throttled(db_session):
    service = AuthService(db_session)
    expires_in = await service.send_otp("+919876543210")
    assert expires_in == 300
    # A second immediate request is rate-limited.
    with pytest.raises(OtpRateLimitError):
        await service.send_otp("+919876543210")


async def test_verify_otp_establishes_session_and_default_role(db_session):
    service = AuthService(db_session)
    result = await service.verify_otp(
        "firebase-token", device_name="Pixel", device_type="android"
    )

    assert result.user.firebase_uid == "firebase-uid-123"
    assert result.user.phone_number == "+919876543210"
    assert result.user.is_phone_verified is True
    assert result.refresh_token  # a refresh token was issued
    assert "farmer" in result.roles  # RBAC default assigned
    assert result.session_id is not None


async def test_login_is_idempotent_for_same_firebase_user(db_session):
    service = AuthService(db_session)
    first = await service.verify_otp("t", device_name=None, device_type=None)
    second = await service.login_google("t", device_name=None, device_type=None)
    assert first.user.id == second.user.id  # same user, no duplicate


async def test_refresh_rotates_and_invalidates_old_token(db_session):
    service = AuthService(db_session)
    result = await service.verify_otp("t", device_name=None, device_type=None)
    old_token = result.refresh_token

    user, new_token = await service.refresh_session(old_token)
    assert user.id == result.user.id
    assert new_token != old_token

    # The old token is now revoked (single-use rotation).
    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh_session(old_token)


async def test_refresh_rejects_unknown_token(db_session):
    service = AuthService(db_session)
    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh_session("does-not-exist")


async def test_profile_upsert_and_fetch(db_session):
    service = AuthService(db_session)
    result = await service.verify_otp("t", device_name=None, device_type=None)

    # No profile yet.
    with pytest.raises(ProfileNotFoundError):
        await service.get_profile(result.user)

    saved = await service.upsert_profile(
        result.user,
        ProfileUpdateRequest(
            full_name="Muthu Kumar",
            language="ta",
            district="madurai",
            block="Melur",
            village="Kottampatti",
            experience_years=12,
            preferred_crops=["paddy", "sugarcane"],
        ),
    )
    assert saved.full_name == "Muthu Kumar"
    assert saved.primary_crop == "paddy"
    assert saved.secondary_crop == "sugarcane"

    fetched = await service.get_profile(result.user)
    assert fetched.id == saved.id

    # Updating again keeps a single profile row.
    updated = await service.upsert_profile(
        result.user,
        ProfileUpdateRequest(full_name="Muthu K", language="en", preferred_crops=[]),
    )
    assert updated.id == saved.id
    assert updated.language == "en"
    assert updated.primary_crop is None


async def test_logout_revokes_refresh_token(db_session):
    service = AuthService(db_session)
    result = await service.verify_otp("t", device_name=None, device_type=None)
    await service.logout(result.user, result.refresh_token)

    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh_session(result.refresh_token)
