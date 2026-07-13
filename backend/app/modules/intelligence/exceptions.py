"""Crop Intelligence exceptions (docs/CODING_STANDARDS.md → Error Handling)."""
from __future__ import annotations

from app.core.exceptions import NotFoundError


class FarmNotOwnedError(NotFoundError):
    # 404 (not 403) so ownership can't be probed by id enumeration.
    error_code = "farm_not_found"
    message = "Farm not found."


class IntelligenceReportNotFoundError(NotFoundError):
    error_code = "intelligence_report_not_found"
    message = "Intelligence report not found."


class IntelligenceUnavailableError(NotFoundError):
    error_code = "intelligence_unavailable"
    message = "No intelligence report yet. Refresh to generate one."
