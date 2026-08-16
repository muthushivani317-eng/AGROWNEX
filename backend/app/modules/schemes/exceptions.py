"""Scheme-specific exceptions (docs/CODING_STANDARDS.md → Error Handling)."""
from __future__ import annotations

from app.core.exceptions import AppError, ConflictError, NotFoundError


class SchemeDataUnavailableError(AppError):
    status_code = 503
    error_code = "scheme_data_unavailable"
    message = "Current verified government scheme data is unavailable."


class SchemeNotFoundError(NotFoundError):
    error_code = "scheme_not_found"
    message = "Scheme not found."


class BookmarkNotFoundError(NotFoundError):
    error_code = "scheme_bookmark_not_found"
    message = "Bookmarked scheme not found."


class BookmarkExistsError(ConflictError):
    error_code = "scheme_bookmark_exists"
    message = "This scheme is already bookmarked."
