"""Typed, public-safe inference failures."""

from app.core.exceptions import AppError


class ModelUnavailableError(AppError):
    status_code = 503
    error_code = "disease_model_unavailable"
    message = "Disease analysis is temporarily unavailable."


class InvalidDiseaseImageError(AppError):
    status_code = 422
    error_code = "invalid_disease_image"
    message = "The supplied image could not be safely processed."
