"""Scheme-specific exceptions (docs/CODING_STANDARDS.md → Error Handling)."""
from __future__ import annotations

from app.core.exceptions import ConflictError, NotFoundError


class SchemeNotFoundError(NotFoundError):
    error_code = "scheme_not_found"
    message = "Scheme not found."


class BookmarkNotFoundError(NotFoundError):
    error_code = "scheme_bookmark_not_found"
    message = "Bookmarked scheme not found."


class BookmarkExistsError(ConflictError):
    error_code = "scheme_bookmark_exists"
    message = "This scheme is already bookmarked."
