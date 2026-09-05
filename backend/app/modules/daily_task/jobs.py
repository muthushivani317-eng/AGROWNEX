"""ARQ background jobs for Today's Farm Task. Registered on the SAME worker
service as the existing market/weather/notification jobs (`app/worker.py`,
`railway.worker.json`) -- no new worker process.

Ordering: `generate_daily_tasks` should fire after the satellite/weather
refresh jobs for the day, since its signal providers consume THEIR
already-computed output rather than triggering fresh Copernicus/Open-Meteo
calls themselves (see the cron schedule change in app/worker.py).
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.daily_task.repository import DailyTaskRepository
from app.modules.daily_task.service import DailyTaskService
from app.modules.farms.models import Farm
from app.modules.farms.repositories import FarmRepository

logger = logging.getLogger(__name__)


async def generate_daily_tasks(session: AsyncSession, *, now: datetime | None = None) -> dict:
    """Idempotent: safe to re-run for the same day (e.g. after a worker
    restart) because `DailyTaskService.generate_tasks_for_farm` dedupes every
    candidate signal against `(dedupe_key, observed_date)` before creating a
    DailySignal row, and the ranking engine's cooldown gate reads
    already-created DailyTask rows, so a second run produces the same
    ranking decision rather than duplicate cards.
    """
    from app.core.config import settings

    if not settings.daily_tasks_enabled:
        return {"skipped": "daily_tasks_enabled is off"}

    now = now or datetime.now(UTC)
    farm_repo = FarmRepository(session)
    repo = DailyTaskRepository(session)

    farms: list[Farm] = await farm_repo.list_active_farms_with_boundary()
    owner_ids = {farm.user_id for farm in farms}
    users_result = await session.execute(select(User).where(User.id.in_(owner_ids)))
    users_by_id = {u.id: u for u in users_result.scalars().all()}

    service = _build_service_for_job(session)

    farms_processed = 0
    tasks_created = 0
    farms_failed = 0
    run_id = uuid.uuid4()

    for farm in farms:
        user = users_by_id.get(farm.user_id)
        if user is None:
            farms_failed += 1
            logger.warning(
                "daily_task.generate_tasks_for_farm: owning user not found",
                extra={"farm_id": str(farm.id), "run_id": str(run_id)},
            )
            continue
        try:
            result = await service.generate_tasks_for_farm(user, farm, now=now)
            tasks_created += len(result.shown)
            farms_processed += 1
        except Exception:  # noqa: BLE001 -- one farm's failure must never abort the batch
            farms_failed += 1
            logger.exception(
                "daily_task.generate_tasks_for_farm failed",
                extra={"farm_id": str(farm.id), "run_id": str(run_id)},
            )

    expired = await repo.expire_stale_active_tasks(now=now)
    await session.commit()

    logger.info(
        "daily_task.generate_daily_tasks complete",
        extra={
            "run_id": str(run_id),
            "farms_processed": farms_processed,
            "farms_failed": farms_failed,
            "tasks_created": tasks_created,
            "tasks_expired": expired,
        },
    )
    return {
        "farms_processed": farms_processed,
        "farms_failed": farms_failed,
        "tasks_created": tasks_created,
        "tasks_expired": expired,
    }


async def send_verification_followups(session: AsyncSession, *, now: datetime | None = None) -> dict:
    """Lighter, separate job for the "was the problem real / did you act /
    do you need help now" check-in. Kept as its own scheduled function so
    its cadence is independent of the once-daily ranking job.
    """
    now = now or datetime.now(UTC)
    repo = DailyTaskRepository(session)
    due = await repo.get_responded_tasks_due_for_verification(now=now)
    sent = 0
    for task in due:
        await repo.mark_verification_sent(task.id, sent_at=now)
        sent += 1
    await session.commit()
    return {"verification_followups_sent": sent}


def _build_service_for_job(session: AsyncSession) -> DailyTaskService:
    """Constructs the same service graph `dependencies.py` builds for a
    request, but directly -- ARQ jobs have no FastAPI `Depends` resolution.
    Kept as one small function so it is the only place that needs updating
    if the provider list or service constructor changes.
    """
    from app.modules.calendar.service import CalendarService
    from app.modules.daily_task.evidence_pack import EvidencePackService
    from app.modules.daily_task.ranking_engine import RankingEngine
    from app.modules.daily_task.repository import DailyTaskRepository as _Repo
    from app.modules.daily_task.repository import DailyTaskZoneRepository
    from app.modules.daily_task.signal_providers import (
        DrainageRiskProvider,
        IrrigationDrynessProvider,
        SowingGerminationProvider,
        UnevenGrowthZoneProvider,
    )
    from app.modules.daily_task.zonal_analysis import ZonalAnalysisService
    from app.modules.disease.storage import get_default_storage
    from app.modules.satellite.service import SatelliteService
    from app.modules.weather.service import WeatherService

    repo = _Repo(session)
    satellite_service = SatelliteService(session, enable_weather=True)
    weather_service = WeatherService(session)
    calendar_service = CalendarService(session, weather_service=weather_service)
    zonal_service = ZonalAnalysisService(satellite_service, DailyTaskZoneRepository(session))
    storage = get_default_storage()  # never None -- see disease/storage.py::get_default_storage

    providers = [
        IrrigationDrynessProvider(satellite_service, weather_service),
        UnevenGrowthZoneProvider(zonal_service),
        DrainageRiskProvider(satellite_service, weather_service),
        SowingGerminationProvider(calendar_service, satellite_service),
    ]
    ranking_engine = RankingEngine(repo)
    evidence_pack_service = EvidencePackService(repo, satellite_service, weather_service, storage)
    return DailyTaskService(repo, providers, ranking_engine, evidence_pack_service)
