"""Market-specific exceptions (docs/CODING_STANDARDS.md → Error Handling)."""
from __future__ import annotations

from app.core.exceptions import AppError, ConflictError, NotFoundError, ValidationError


class MarketDataUnavailableError(AppError):
    """No price source responded and no cached/stored prices exist to fall back to."""

    status_code = 503
    error_code = "market_data_unavailable"
    message = "Market prices are temporarily unavailable. Please try again."


class MarketRequestError(ValidationError):
    error_code = "market_request_invalid"
    message = "Provide a crop and market to view price history."


class FavouriteNotFoundError(NotFoundError):
    error_code = "market_favourite_not_found"
    message = "Favourite market not found."


class FavouriteExistsError(ConflictError):
    error_code = "market_favourite_exists"
    message = "This market is already in your favourites."
