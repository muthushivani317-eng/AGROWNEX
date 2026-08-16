"""Nutrient module exceptions (docs/CODING_STANDARDS.md → Error Handling).

Image-quality and no-plant errors are reused from the Disease module so the two
image pipelines share one contract (no duplicate error codes).
"""

from __future__ import annotations

from app.core.exceptions import AppError, NotFoundError

# Reused so the nutrient and disease image pipelines share one error contract.
from app.modules.disease.exceptions import (  # noqa: F401 — re-exported for the service
    NoPlantDetectedError,
    PoorImageQualityError,
)


class FarmNotOwnedError(NotFoundError):
    # 404 (not 403) so ownership can't be probed by id enumeration.
    error_code = "farm_not_found"
    message = "Farm not found."


class NutrientReportNotFoundError(NotFoundError):
    error_code = "nutrient_report_not_found"
    message = "Nutrient report not found."


class NutrientDataUnavailableError(NotFoundError):
    error_code = "nutrient_data_unavailable"
    message = "No nutrient analysis is available for this farm yet."


class NutrientAnalysisError(AppError):
    status_code = 503
    error_code = "nutrient_analysis_failed"
    message = "Could not analyse the image right now. Please try again."


class NutrientProviderUnavailableError(AppError):
    status_code = 503
    error_code = "analysis_unavailable"
    message = "Nutrient image analysis is unavailable right now."


class NutrientCropMismatchError(AppError):
    status_code = 422
    error_code = "nutrient_crop_mismatch"
    message = "The selected crop does not match this farm."


class NutrientUnsupportedCropError(AppError):
    status_code = 422
    error_code = "nutrient_unsupported_crop"
    message = "This crop is not supported for nutrient image assessment."
