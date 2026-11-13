"""Growth-specific exceptions (docs/CODING_STANDARDS.md → Error Handling).

Reuses the Disease pipeline's image-quality and analysis errors so the client
handles a single, consistent set of error codes across photo features.
"""

from __future__ import annotations

from app.core.exceptions import AppError, NotFoundError, ValidationError

# Reuse the Disease pipeline's image errors (docs: reuse, no duplication).
from app.modules.disease.exceptions import (  # noqa: F401 — re-exported
    NoPlantDetectedError,
    PoorImageQualityError,
)


class GrowthAnalysisError(AppError):
    """The growth model produced no usable structured result."""

    status_code = 502
    error_code = "growth_analysis_failed"
    message = "Could not analyse the crop photo. Please try again."


class GrowthSessionNotFoundError(NotFoundError):
    error_code = "growth_session_not_found"
    message = "Growth session not found."


class GrowthImageNotFoundError(NotFoundError):
    error_code = "growth_image_not_found"
    message = "Growth photo not found."


class FarmNotFoundError(NotFoundError):
    error_code = "farm_not_found"
    message = "Farm not found."


class GroundnutStageConfirmationError(ValidationError):
    error_code = "groundnut_stage_confirmation_invalid"
    message = "The Groundnut growth-stage decision is invalid."
