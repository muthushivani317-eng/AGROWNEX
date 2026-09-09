import uuid

from fastapi import APIRouter

from app.modules.auth.dependencies import CurrentUser
from app.schemas.response import SuccessResponse, success

from .dependencies import OrganicAdvisoryServiceDep
from .schemas import (
    OrganicWeatherMetricsOut,
    SatelliteFindingIn,
    SatelliteFindingOut,
    SatelliteScoutingIn,
    SatelliteScoutingOut,
    TrustedWeatherGateIn,
    TrustedWeatherGateOut,
    WeatherOrganicGateIn,
    WeatherOrganicGateOut,
)

router = APIRouter(prefix="/organic-advisories", tags=["organic-advisories"])


@router.get(
    "/farms/{farm_id}/trusted-weather-metrics",
    response_model=SuccessResponse[OrganicWeatherMetricsOut],
)
async def trusted_weather_metrics(
    farm_id: uuid.UUID, current_user: CurrentUser, service: OrganicAdvisoryServiceDep
):
    return success(await service.weather_metrics(current_user, farm_id))


@router.post("/trusted-weather-gates", response_model=SuccessResponse[TrustedWeatherGateOut])
async def trusted_weather_gate(
    payload: TrustedWeatherGateIn, current_user: CurrentUser, service: OrganicAdvisoryServiceDep
):
    return success(await service.trusted_weather_gate(current_user, payload))


@router.post("/weather-gates", response_model=SuccessResponse[WeatherOrganicGateOut])
async def weather_gate(
    payload: WeatherOrganicGateIn,
    current_user: CurrentUser,
    service: OrganicAdvisoryServiceDep,
):
    return success(await service.weather_gate(current_user, payload))


@router.post("/satellite-scouting", response_model=SuccessResponse[SatelliteScoutingOut])
async def satellite_scouting(
    payload: SatelliteScoutingIn,
    current_user: CurrentUser,
    service: OrganicAdvisoryServiceDep,
):
    return success(await service.satellite_scouting(current_user, payload))


@router.post(
    "/satellite-scouting/{action_id}/findings",
    response_model=SuccessResponse[SatelliteFindingOut],
)
async def satellite_findings(
    action_id: uuid.UUID,
    payload: SatelliteFindingIn,
    current_user: CurrentUser,
    service: OrganicAdvisoryServiceDep,
):
    return success(await service.record_satellite_findings(current_user, action_id, payload))
