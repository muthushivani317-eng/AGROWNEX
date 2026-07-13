"""Soil Intelligence exceptions (docs/CODING_STANDARDS.md → Error Handling)."""
from __future__ import annotations

from app.core.exceptions import NotFoundError, ValidationError


class FarmNotOwnedError(NotFoundError):
    # 404 (not 403) so ownership can't be probed by id enumeration.
    error_code = "farm_not_found"
    message = "Farm not found."


class SoilReportNotFoundError(NotFoundError):
    error_code = "soil_report_not_found"
    message = "Soil report not found."


class SoilDataUnavailableError(NotFoundError):
    error_code = "soil_data_unavailable"
    message = "No soil data is available for this farm yet."


class InvalidSoilReportError(ValidationError):
    error_code = "invalid_soil_report"
    message = "The soil report is invalid."
