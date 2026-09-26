"""Domain exception hierarchy (docs/CODING_STANDARDS.md → Error Handling).

Services raise these; the global handlers in `app.api.errors` translate them
into the standard error envelope. Never swallow exceptions silently.
"""
from __future__ import annotations


class AppError(Exception):
    """Base application error mapped to an HTTP response."""

    status_code: int = 500
    error_code: str = "internal_error"
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        error_code: str | None = None,
        status_code: int | None = None,
        details: dict[str, str] | None = None,
    ) -> None:
        self.message = message or self.message
        if error_code is not None:
            self.error_code = error_code
        if status_code is not None:
            self.status_code = status_code
        # Optional small string map for a client to build a more specific,
        # localized message than the fixed `message` field allows (e.g. which
        # crop was expected vs observed) -- never anything sensitive, always
        # safe to surface directly to the end user.
        self.details = details
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = 404
    error_code = "not_found"
    message = "Resource not found."


class ValidationError(AppError):
    status_code = 422
    error_code = "validation_error"
    message = "Validation failed."


class UnauthorizedError(AppError):
    status_code = 401
    error_code = "unauthorized"
    message = "Authentication required."


class ForbiddenError(AppError):
    status_code = 403
    error_code = "forbidden"
    message = "You do not have permission to perform this action."


class ConflictError(AppError):
    status_code = 409
    error_code = "conflict"
    message = "The request conflicts with the current state."


class QuotaExceededError(AppError):
    """A farmer's daily AI quota is exhausted (protects the shared Gemini budget)."""

    status_code = 429
    error_code = "ai_daily_quota_exceeded"
    message = (
        "உங்கள் வரம்பு முடிந்துவிட்டது. பிறகு முயற்சிக்கவும். "
        "/ Your limit has been reached. Try again later."
    )
