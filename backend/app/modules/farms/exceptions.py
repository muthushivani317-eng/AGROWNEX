"""Farm-specific exceptions (docs/CODING_STANDARDS.md → Error Handling)."""
from __future__ import annotations

from app.core.exceptions import ConflictError, NotFoundError, ValidationError


class FarmNotFoundError(NotFoundError):
    error_code = "farm_not_found"
    message = "Farm not found."


class DuplicateFarmError(ConflictError):
    error_code = "duplicate_farm"
    message = "You already have a farm with this name."


class InvalidBoundaryError(ValidationError):
    error_code = "invalid_boundary"
    message = "The farm boundary is invalid."
