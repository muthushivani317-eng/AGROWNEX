"""Disease-specific exceptions (docs/CODING_STANDARDS.md → Error Handling)."""
from __future__ import annotations

from app.core.exceptions import AppError, NotFoundError, ValidationError


class PoorImageQualityError(ValidationError):
    """Raised when an image fails the quality gate — it is never sent to Gemini."""

    error_code = "poor_image_quality"
    message = "The photo quality is too low. Please take a clearer photo."

    def __init__(self, issues: list[str]) -> None:
        super().__init__(self.message)
        self.issues = issues


class NoPlantDetectedError(ValidationError):
    """Raised when Gemini reports the photo has no plant/leaf (docs: STEP 2)."""

    error_code = "no_plant_detected"
    message = "No plant or leaf detected. Please photograph the affected leaf clearly."

    def __init__(self, reason: str | None = None) -> None:
        super().__init__(self.message)
        self.reason = reason


class DiseaseAnalysisError(AppError):
    status_code = 503
    error_code = "disease_analysis_failed"
    message = "Could not analyse the image right now. Please try again."


class DiseaseReportNotFoundError(NotFoundError):
    error_code = "disease_report_not_found"
    message = "Disease report not found."
