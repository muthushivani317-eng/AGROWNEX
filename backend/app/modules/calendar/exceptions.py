"""Calendar-specific exceptions (docs/CODING_STANDARDS.md → Error Handling)."""
from __future__ import annotations

from app.core.exceptions import NotFoundError, ValidationError


class FarmNotFoundError(NotFoundError):
    error_code = "farm_not_found"
    message = "Farm not found."


class CalendarEventNotFoundError(NotFoundError):
    error_code = "calendar_event_not_found"
    message = "Calendar activity not found."


class SowingDateRequiredError(ValidationError):
    """A calendar cannot be generated without a sowing date (docs: inputs)."""

    error_code = "sowing_date_required"
    message = "Set the crop and sowing date for this farm before generating a calendar."
