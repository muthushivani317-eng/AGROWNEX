"""FastAPI dependency wiring for the daily_task module. Mirrors the existing
per-module `dependencies.py` pattern (`app/modules/market/dependencies.py`):
`Annotated[Type, Depends(factory)]` aliases built once, imported and used
directly as parameter type annotations in routes.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.auth.dependencies import CurrentUser
from app.modules.calendar.service import CalendarService
from app.modules.daily_task.evidence_pack import EvidencePackService
from app.modules.daily_task.ranking_engine import RankingEngine
from app.modules.daily_task.repository import DailyTaskRepository, DailyTaskZoneRepository
from app.modules.daily_task.service import DailyTaskService
from app.modules.daily_task.signal_providers import (
    DrainageRiskProvider,
    IrrigationDrynessProvider,
    SowingGerminationProvider,
    UnevenGrowthZoneProvider,
)
from app.modules.daily_task.zonal_analysis import ZonalAnalysisService
from app.modules.disease.storage import ObjectStorage, get_default_storage
from app.modules.satellite.service import SatelliteService
from app.modules.weather.service import WeatherService

__all__ = [
    "CurrentUser",
    "DailyTaskRepositoryDep",
    "DailyTaskZoneRepositoryDep",
    "DailyTaskServiceDep",
    "EvidencePackServiceDep",
    "ObjectStorageDep",
]


def get_daily_task_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DailyTaskRepository:
    return DailyTaskRepository(session)


def get_daily_task_zone_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DailyTaskZoneRepository:
    return DailyTaskZoneRepository(session)


def get_ranking_engine(
    repo: Annotated[DailyTaskRepository, Depends(get_daily_task_repository)],
) -> RankingEngine:
    return RankingEngine(repo)


def get_object_storage() -> ObjectStorage:
    # `get_default_storage()` always returns a usable object (R2Client /
    # MockStorage / UnavailableStorage) -- never None. A `.put()` call against
    # UnavailableStorage raises StorageUnavailableError, which callers here
    # catch to degrade gracefully rather than checking for a None storage.
    return get_default_storage()


def get_satellite_service_for_daily_task(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SatelliteService:
    return SatelliteService(session, enable_weather=True)


def get_weather_service_for_daily_task(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> WeatherService:
    return WeatherService(session)


def get_calendar_service_for_daily_task(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CalendarService:
    return CalendarService(session, weather_service=WeatherService(session))


def get_zonal_analysis_service(
    satellite_service: Annotated[SatelliteService, Depends(get_satellite_service_for_daily_task)],
    zone_repo: Annotated[DailyTaskZoneRepository, Depends(get_daily_task_zone_repository)],
) -> ZonalAnalysisService:
    return ZonalAnalysisService(satellite_service, zone_repo)


def get_signal_providers(
    satellite_service: Annotated[SatelliteService, Depends(get_satellite_service_for_daily_task)],
    weather_service: Annotated[WeatherService, Depends(get_weather_service_for_daily_task)],
    calendar_service: Annotated[CalendarService, Depends(get_calendar_service_for_daily_task)],
    zonal_service: Annotated[ZonalAnalysisService, Depends(get_zonal_analysis_service)],
) -> list:
    return [
        IrrigationDrynessProvider(satellite_service, weather_service),
        UnevenGrowthZoneProvider(zonal_service),
        DrainageRiskProvider(satellite_service, weather_service),
        SowingGerminationProvider(calendar_service, satellite_service),
    ]


def get_evidence_pack_service(
    repo: Annotated[DailyTaskRepository, Depends(get_daily_task_repository)],
    satellite_service: Annotated[SatelliteService, Depends(get_satellite_service_for_daily_task)],
    weather_service: Annotated[WeatherService, Depends(get_weather_service_for_daily_task)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
) -> EvidencePackService:
    return EvidencePackService(repo, satellite_service, weather_service, storage)


def get_daily_task_service(
    repo: Annotated[DailyTaskRepository, Depends(get_daily_task_repository)],
    providers: Annotated[list, Depends(get_signal_providers)],
    ranking_engine: Annotated[RankingEngine, Depends(get_ranking_engine)],
    evidence_pack_service: Annotated[EvidencePackService, Depends(get_evidence_pack_service)],
) -> DailyTaskService:
    return DailyTaskService(repo, providers, ranking_engine, evidence_pack_service)


DailyTaskRepositoryDep = Annotated[DailyTaskRepository, Depends(get_daily_task_repository)]
DailyTaskZoneRepositoryDep = Annotated[DailyTaskZoneRepository, Depends(get_daily_task_zone_repository)]
DailyTaskServiceDep = Annotated[DailyTaskService, Depends(get_daily_task_service)]
EvidencePackServiceDep = Annotated[EvidencePackService, Depends(get_evidence_pack_service)]
ObjectStorageDep = Annotated[ObjectStorage, Depends(get_object_storage)]
