"""Weather-specific exceptions (docs/CODING_STANDARDS.md → Error Handling)."""
from __future__ import annotations

from app.core.exceptions import AppError, ValidationError


class WeatherUnavailableError(AppError):
    status_code = 503
    error_code = "weather_unavailable"
    message = "Weather service is temporarily unavailable. Please try again."


class FarmLocationMissingError(ValidationError):
    error_code = "farm_location_missing"
    message = "This farm has no GPS location yet. Add a location to see weather."


class WeatherRequestError(ValidationError):
    error_code = "weather_request_invalid"
    message = "Provide a farm_id, or latitude and longitude."
