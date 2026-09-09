from fastapi import APIRouter

from app.modules.auth.dependencies import CurrentUser
from app.schemas.response import SuccessResponse, success

from .dependencies import OrganicAdvisoryServiceDep
from .schemas import (
    SatelliteScoutingIn,
    SatelliteScoutingOut,
    WeatherOrganicGateIn,
    WeatherOrganicGateOut,
)

router = APIRouter(prefix="/organic-advisories", tags=["organic-advisories"])


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
