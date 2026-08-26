"""Produce-specific exceptions (docs/CODING_STANDARDS.md → Error Handling)."""

from __future__ import annotations

from app.core.exceptions import NotFoundError, ValidationError


class ProduceOfferNotFoundError(NotFoundError):
    error_code = "produce_offer_not_found"
    message = "Produce offer not found."


class FarmNotOwnedError(NotFoundError):
    # 404 (not 403) so ownership can't be probed by id enumeration.
    error_code = "farm_not_found"
    message = "Farm not found."


class InvalidProduceError(ValidationError):
    error_code = "invalid_produce"
    message = "The produce offer is invalid."


class InvalidStatusTransitionError(ValidationError):
    error_code = "invalid_produce_status"
    message = "This status change is not allowed."
