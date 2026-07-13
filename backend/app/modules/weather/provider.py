"""Open-Meteo client (docs/PRODUCT_RULES.md rule 5).

The external data source for weather. Isolated behind a small interface so the
service can be tested with a fake provider (no network), and so retry/timeout
policy lives in one place.
"""
from __future__ import annotations

import asyncio
from typing import Any, Protocol

import httpx

from app.core.logging import get_logger
from app.modules.weather.constants import (
    CURRENT_FIELDS,
    DAILY_FIELDS,
    FORECAST_DAYS,
    HOURLY_FIELDS,
    OPEN_METEO_BASE_URL,
    OPEN_METEO_MAX_RETRIES,
    OPEN_METEO_TIMEOUT_SECONDS,
)
from app.modules.weather.exceptions import WeatherUnavailableError

logger = get_logger("weather.provider")


class ForecastProvider(Protocol):
    """Fetches a raw Open-Meteo forecast payload for a coordinate."""

    async def fetch(self, latitude: float, longitude: float) -> dict[str, Any]: ...


class OpenMeteoClient:
    """Real Open-Meteo forecast client with timeout + bounded retries."""

    def __init__(
        self,
        base_url: str = OPEN_METEO_BASE_URL,
        *,
        timeout: float = OPEN_METEO_TIMEOUT_SECONDS,
        max_retries: int = OPEN_METEO_MAX_RETRIES,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    def _params(self, latitude: float, longitude: float) -> dict[str, Any]:
        return {
            "latitude": latitude,
            "longitude": longitude,
            "current": ",".join(CURRENT_FIELDS),
            "hourly": ",".join(HOURLY_FIELDS),
            "daily": ",".join(DAILY_FIELDS),
            "timezone": "auto",
            "forecast_days": FORECAST_DAYS,
            "wind_speed_unit": "kmh",
            "temperature_unit": "celsius",
            "precipitation_unit": "mm",
        }

    async def fetch(self, latitude: float, longitude: float) -> dict[str, Any]:
        url = f"{self.base_url}/forecast"
        params = self._params(latitude, longitude)
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    return response.json()
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_error = exc
            except httpx.HTTPStatusError as exc:
                # Retry 5xx; surface client errors immediately.
                if exc.response.status_code < 500:
                    raise WeatherUnavailableError() from exc
                last_error = exc

            if attempt < self.max_retries:
                await asyncio.sleep(min(0.5 * 2 ** (attempt - 1), 4.0))

        logger.warning("Open-Meteo fetch failed after %s attempts", self.max_retries)
        raise WeatherUnavailableError() from last_error
