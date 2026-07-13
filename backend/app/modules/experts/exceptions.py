"""Expert Connect exceptions (docs/CODING_STANDARDS.md → Error Handling)."""
from __future__ import annotations

from app.core.exceptions import NotFoundError, ValidationError


class ExpertNotFoundError(NotFoundError):
    error_code = "expert_not_found"
    message = "Expert not found."


class ConsultationNotFoundError(NotFoundError):
    error_code = "consultation_not_found"
    message = "Consultation not found."


class FarmNotOwnedError(NotFoundError):
    # 404 (not 403) so ownership can't be probed by id enumeration.
    error_code = "farm_not_found"
    message = "Farm not found."


class InvalidConsultationError(ValidationError):
    error_code = "invalid_consultation"
    message = "The consultation is invalid."


class ConsultationClosedError(ValidationError):
    error_code = "consultation_closed"
    message = "This consultation is closed and can no longer be changed."


class InvalidStatusTransitionError(ValidationError):
    error_code = "invalid_consultation_status"
    message = "This status change is not allowed."
