"""Auth-specific exceptions."""
from __future__ import annotations

from app.core.exceptions import AppError, NotFoundError, UnauthorizedError


class UserNotFoundError(NotFoundError):
    error_code = "user_not_found"
    message = "User not found."


class ProfileNotFoundError(NotFoundError):
    error_code = "profile_not_found"
    message = "Farmer profile not found."


class InvalidTokenError(UnauthorizedError):
    error_code = "invalid_token"
    message = "Invalid or expired authentication token."


class InvalidRefreshTokenError(UnauthorizedError):
    error_code = "invalid_refresh_token"
    message = "The refresh token is invalid, revoked, or expired."


class OtpRateLimitError(AppError):
    status_code = 429
    error_code = "otp_rate_limited"
    message = "Too many OTP requests. Please wait before trying again."
