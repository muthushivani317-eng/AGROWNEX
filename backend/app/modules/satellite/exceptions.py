"""Satellite Intelligence exceptions (docs/CODING_STANDARDS.md → Error Handling)."""
from __future__ import annotations

from app.core.exceptions import NotFoundError


class FarmNotOwnedError(NotFoundError):
    # 404 (not 403) so ownership can't be probed by id enumeration.
    error_code = "farm_not_found"
    message = "Farm not found."


class SatelliteSessionNotFoundError(NotFoundError):
    error_code = "satellite_session_not_found"
    message = "Satellite session not found."


class SatelliteUnavailableError(NotFoundError):
    error_code = "satellite_unavailable"
    message = "No satellite imagery is available for this farm yet."
