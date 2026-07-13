"""Weather API routes (docs/API_CONTRACT.md → WEATHER MODULE).

    GET /weather            (full bundle: current + hourly + daily + insights)
    GET /weather/current
    GET /weather/forecast   (hourly + daily)
    GET /weather/alerts     (deterministic insights)

Each accepts a `farm_id` (coordinates resolved from the farm, ownership-scoped)
or explicit `latitude`/`longitude`.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.modules.weather.dependencies import CurrentUser, WeatherServiceDep
from app.modules.weather.exceptions import WeatherRequestError
from app.modules.weather.schemas import (
    AlertsOut,
    CurrentWeather,
    ForecastOut,
    WeatherBundle,
)
from app.modules.weather.service import WeatherService
from app.schemas.response import SuccessResponse, success

router = APIRouter(prefix="/weather", tags=["weather"])


async def _resolve(
    current_user: CurrentUser,
    service: WeatherService,
    farm_id: uuid.UUID | None,
    latitude: float | None,
    longitude: float | None,
) -> WeatherBundle:
    if farm_id is not None:
        return await service.get_by_farm(current_user, farm_id)
    if latitude is not None and longitude is not None:
        return await service.get_by_coordinates(latitude, longitude)
    raise WeatherRequestError()


FarmIdQuery = Query(None, description="Farm to read weather for (uses its GPS)")
LatQuery = Query(None, ge=-90, le=90)
LngQuery = Query(None, ge=-180, le=180)


@router.get("", response_model=SuccessResponse[WeatherBundle])
async def get_weather(
    current_user: CurrentUser,
    service: WeatherServiceDep,
    farm_id: uuid.UUID | None = FarmIdQuery,
    latitude: float | None = LatQuery,
    longitude: float | None = LngQuery,
):
    """Full weather bundle for a farm (or coordinates)."""
    bundle = await _resolve(current_user, service, farm_id, latitude, longitude)
    return success(bundle)


@router.get("/current", response_model=SuccessResponse[CurrentWeather])
async def get_current(
    current_user: CurrentUser,
    service: WeatherServiceDep,
    farm_id: uuid.UUID | None = FarmIdQuery,
    latitude: float | None = LatQuery,
    longitude: float | None = LngQuery,
):
    """Current conditions."""
    bundle = await _resolve(current_user, service, farm_id, latitude, longitude)
    return success(bundle.current)


@router.get("/forecast", response_model=SuccessResponse[ForecastOut])
async def get_forecast(
    current_user: CurrentUser,
    service: WeatherServiceDep,
    farm_id: uuid.UUID | None = FarmIdQuery,
    latitude: float | None = LatQuery,
    longitude: float | None = LngQuery,
):
    """24-hour hourly + 7-day daily forecast."""
    bundle = await _resolve(current_user, service, farm_id, latitude, longitude)
    return success(ForecastOut(hourly=bundle.hourly, daily=bundle.daily))


@router.get("/alerts", response_model=SuccessResponse[AlertsOut])
async def get_alerts(
    current_user: CurrentUser,
    service: WeatherServiceDep,
    farm_id: uuid.UUID | None = FarmIdQuery,
    latitude: float | None = LatQuery,
    longitude: float | None = LngQuery,
):
    """Deterministic, rule-based agricultural insights."""
    bundle = await _resolve(current_user, service, farm_id, latitude, longitude)
    return success(AlertsOut(insights=bundle.insights))
