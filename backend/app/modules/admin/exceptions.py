"""Admin exceptions (docs/CODING_STANDARDS.md → Error Handling)."""
from __future__ import annotations

from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError


class NotAnAdminError(ForbiddenError):
    error_code = "not_an_admin"
    message = "Admin access is required."


class AdminSuspendedError(ForbiddenError):
    error_code = "admin_suspended"
    message = "This admin account is suspended."


class PermissionDeniedError(ForbiddenError):
    error_code = "permission_denied"
    message = "You do not have permission to perform this action."


class FarmerNotFoundError(NotFoundError):
    error_code = "farmer_not_found"
    message = "Farmer not found."


class OfferNotFoundError(NotFoundError):
    error_code = "offer_not_found"
    message = "Produce offer not found."


class InvalidBroadcastError(ValidationError):
    error_code = "invalid_broadcast"
    message = "The broadcast is invalid."


class InvalidProcurementStatusError(ValidationError):
    error_code = "invalid_procurement_status"
    message = "Invalid procurement status."
