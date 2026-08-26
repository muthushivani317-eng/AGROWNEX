"""Auth API routes (docs/API_CONTRACT.md → AUTH MODULE).

Identity is verified by Firebase (docs/SECURITY.md → Firebase JWT); these routes
add server-side session management, profile setup, and RBAC preparation. Every
handler is thin — all logic lives in `AuthService`.
"""
from __future__ import annotations

from fastapi import APIRouter, status

from app.modules.auth.dependencies import AuthServiceDep, CurrentUser
from app.modules.auth.schemas import (
    OtpSendRequest,
    OtpSendResponse,
    ProfileOut,
    ProfileUpdateRequest,
    RefreshRequest,
    SessionOut,
    SocialLoginRequest,
    UserOut,
)
from app.modules.auth.service import SessionResult
from app.schemas.response import SuccessResponse, success

router = APIRouter(prefix="/auth", tags=["auth"])


def _to_session_out(result: SessionResult) -> SessionOut:
    return SessionOut(
        user=UserOut.model_validate(result.user),
        profile=(
            ProfileOut.model_validate(result.profile) if result.profile else None
        ),
        roles=result.roles,
        refresh_token=result.refresh_token,
        session_id=result.session_id,
    )


@router.post("/otp/send", response_model=SuccessResponse[OtpSendResponse])
async def send_otp(payload: OtpSendRequest, service: AuthServiceDep):
    """Record/throttle an OTP dispatch (Firebase sends the SMS on-device)."""
    expires_in = await service.send_otp(payload.phone_number)
    return success(
        OtpSendResponse(sent=True, expires_in=expires_in), message="OTP sent"
    )


@router.post("/otp/verify", response_model=SuccessResponse[SessionOut])
async def verify_otp(payload: SocialLoginRequest, service: AuthServiceDep):
    """Verify the Firebase phone token and establish a session."""
    result = await service.verify_otp(
        payload.id_token,
        device_name=payload.device_name,
        device_type=payload.device_type,
    )
    return success(_to_session_out(result), message="Phone verified")


@router.post("/google", response_model=SuccessResponse[SessionOut])
async def login_google(payload: SocialLoginRequest, service: AuthServiceDep):
    """Verify a Google-issued Firebase token and establish a session."""
    result = await service.login_google(
        payload.id_token,
        device_name=payload.device_name,
        device_type=payload.device_type,
    )
    return success(_to_session_out(result), message="Signed in with Google")


@router.post("/apple", response_model=SuccessResponse[SessionOut])
async def login_apple(payload: SocialLoginRequest, service: AuthServiceDep):
    """Verify an Apple-issued Firebase token and establish a session."""
    result = await service.login_apple(
        payload.id_token,
        device_name=payload.device_name,
        device_type=payload.device_type,
    )
    return success(_to_session_out(result), message="Signed in with Apple")


@router.post("/refresh", response_model=SuccessResponse[dict])
async def refresh(payload: RefreshRequest, service: AuthServiceDep):
    """Rotate the server refresh token (single-use)."""
    user, new_token = await service.refresh_session(payload.refresh_token)
    return success(
        {"user_id": str(user.id), "refresh_token": new_token},
        message="Session refreshed",
    )


@router.get("/profile", response_model=SuccessResponse[UserOut])
async def get_account(current_user: CurrentUser):
    """Return the authenticated user's account record."""
    return success(UserOut.model_validate(current_user))


@router.get("/profile/details", response_model=SuccessResponse[ProfileOut])
async def get_profile(current_user: CurrentUser, service: AuthServiceDep):
    """Return the authenticated user's farmer profile."""
    profile = await service.get_profile(current_user)
    return success(ProfileOut.model_validate(profile))


@router.put("/profile", response_model=SuccessResponse[ProfileOut])
async def update_profile(
    payload: ProfileUpdateRequest,
    current_user: CurrentUser,
    service: AuthServiceDep,
):
    """Create or update the farmer profile (profile-setup step)."""
    profile = await service.upsert_profile(current_user, payload)
    return success(ProfileOut.model_validate(profile), message="Profile saved")


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    current_user: CurrentUser,
    service: AuthServiceDep,
    payload: RefreshRequest | None = None,
):
    """Revoke the session (single refresh token, or all when none is given)."""
    await service.logout(current_user, payload.refresh_token if payload else None)
    return success(None, message="Logged out")


@router.delete("/account", status_code=status.HTTP_200_OK)
async def close_account(current_user: CurrentUser, service: AuthServiceDep):
    """Close the farmer account and revoke all active server sessions."""
    await service.close_account(current_user)
    return success(None, message="Account closed")
