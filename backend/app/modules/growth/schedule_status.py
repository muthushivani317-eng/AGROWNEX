"""Growth Monitor "behind schedule" check (owner decision, 2026-09-25).

Behind schedule = an overdue organic task OR the crop's stage lagging what the
verified crop calendar expects for its age. Deterministic and fail-closed: no
verified calendar, no sowing date, or no recent stage evidence → no stage claim.
When behind, the app leads the Growth Monitor with the organic growth boost.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.timezone import today_ist
from app.modules.calendar.registry import ACTIVE_CROP_STAGE_REGISTRY, CropStageRegistry
from app.modules.growth.models import CropGrowthAnalysis, CropGrowthSession, CropStageState
from app.modules.organic_mvp.models import OrganicCropCycle, OrganicPlot, OrganicScheduledTask

# Generic stage rank; germination and seedling are both "early".
STAGE_RANK = {
    "germination": 0, "seedling": 0, "vegetative": 1, "flowering": 2,
    "fruiting": 3, "maturity": 4, "harvest": 5,
}

# Verified-calendar stage codes → generic stage. Activity-only windows
# (irrigation, weeding, scouting, multi-year care) map to nothing on purpose.
CALENDAR_TO_GENERIC: dict[str, str] = {
    **dict.fromkeys((
        "nursery_raising", "nursery_seedling", "sowing", "sowing_and_basal_dose",
        "sowing_and_establishment", "sowing_and_thinning", "planting",
        "planting_and_basin_establishment", "planting_and_establishment", "transplanting",
        "transplanting_establishment", "establishment", "early_growth_establishment",
        "establishment_and_weed_management",
    ), "seedling"),
    **dict.fromkeys((
        "vegetative_growth", "vegetative_growth_earthing_up", "vegetative_growth_nutrient_mgmt",
        "vegetative_tillering", "tillering_and_early_growth", "establishment_and_vegetative_growth",
        "grand_growth", "panicle_initiation",
    ), "vegetative"),
    **dict.fromkeys((
        "booting_heading_flowering", "flowering", "flowering_pegging",
        "flowering_tasseling_silking", "flowering_to_fruit_set", "squaring_and_flowering",
        "flowering_fruit_development", "bunch_emergence_and_propping",
    ), "flowering"),
    **dict.fromkeys((
        "fruit_development", "pod_development", "milk_dough_grain_filling", "bunch_development",
        "rhizome_development_bulking", "boll_development_and_maturity",
    ), "fruiting"),
    **dict.fromkeys((
        "grain_filling_and_maturity", "maturation", "maturity_and_harvest",
        "maturity_and_ripening", "maturity_harvest", "harvest_and_maturity",
    ), "maturity"),
    **dict.fromkeys((
        "harvest", "harvesting", "harvest_and_extended_picking", "picking_and_harvest",
    ), "harvest"),
}

MIN_PHOTO_CONFIDENCE = 60  # AI stage must be at least this confident to count
EVIDENCE_MAX_AGE_DAYS = 21  # older photos/confirmations can't say today's stage


@dataclass
class ScheduleStatus:
    behind: bool = False
    reasons: list[str] = field(default_factory=list)
    overdue_tasks: int = 0
    expected_stage: str | None = None
    observed_stage: str | None = None
    calendar_available: bool = False

    def as_dict(self) -> dict:
        return {
            "behind": self.behind, "reasons": self.reasons,
            "overdue_tasks": self.overdue_tasks, "expected_stage": self.expected_stage,
            "observed_stage": self.observed_stage, "calendar_available": self.calendar_available,
        }


def expected_generic_stage(
    registry: CropStageRegistry, crop: str | None, sowing_date: date | None, today: date
) -> tuple[bool, str | None]:
    """(calendar available, earliest generic stage expected at this crop age)."""
    schedule = registry.resolve(crop)
    if schedule is None:
        return False, None
    if sowing_date is None or sowing_date > today:
        return True, None
    age = (today - sowing_date).days
    stages = [
        CALENDAR_TO_GENERIC[s.code] for s in schedule.stages
        if s.start_offset <= age <= s.end_offset and s.code in CALENDAR_TO_GENERIC
    ]
    # Earliest matching stage: overlapping windows never produce a false alarm.
    return True, min(stages, key=STAGE_RANK.__getitem__) if stages else None


def is_lagging(expected: str | None, observed: str | None) -> bool:
    if expected not in STAGE_RANK or observed not in STAGE_RANK:
        return False
    return STAGE_RANK[observed] < STAGE_RANK[expected]


async def _overdue_tasks(session: AsyncSession, farm_id: uuid.UUID, today: date) -> int:
    stmt = (
        select(func.count(OrganicScheduledTask.id))
        .join(OrganicCropCycle, OrganicCropCycle.id == OrganicScheduledTask.crop_cycle_id)
        .join(OrganicPlot, OrganicPlot.id == OrganicCropCycle.plot_id)
        .where(
            OrganicPlot.farm_id == farm_id,
            OrganicScheduledTask.status == "pending",
            OrganicScheduledTask.due_on < today,
        )
    )
    return int((await session.execute(stmt)).scalar_one() or 0)


async def _observed_stage(
    session: AsyncSession, user_id: uuid.UUID, farm_id: uuid.UUID
) -> str | None:
    """Most recent stage evidence: farmer-confirmed stage or a confident photo."""
    since = datetime.now(UTC) - timedelta(days=EVIDENCE_MAX_AGE_DAYS)
    candidates: list[tuple[datetime, str]] = []
    confirmed = (await session.execute(
        select(CropStageState.confirmed_stage, CropStageState.updated_at)
        .where(
            CropStageState.user_id == user_id, CropStageState.farm_id == farm_id,
            CropStageState.is_deleted.is_(False), CropStageState.confirmed_stage.is_not(None),
            CropStageState.state.in_(("confirmed", "corrected")),
        )
        .order_by(CropStageState.updated_at.desc()).limit(1)
    )).first()
    if confirmed is not None:
        candidates.append((confirmed.updated_at, confirmed.confirmed_stage))
    photo = (await session.execute(
        select(CropGrowthAnalysis.growth_stage, CropGrowthAnalysis.created_at)
        .join(CropGrowthSession, CropGrowthSession.id == CropGrowthAnalysis.session_id)
        .where(
            CropGrowthSession.user_id == user_id, CropGrowthSession.farm_id == farm_id,
            CropGrowthSession.is_deleted.is_(False),
            CropGrowthAnalysis.confidence >= MIN_PHOTO_CONFIDENCE,
        )
        .order_by(CropGrowthAnalysis.created_at.desc()).limit(1)
    )).first()
    if photo is not None:
        candidates.append((photo.created_at, photo.growth_stage))
    fresh = [
        (at if at.tzinfo else at.replace(tzinfo=UTC), stage)
        for at, stage in candidates if at is not None and stage in STAGE_RANK
    ]
    fresh = [item for item in fresh if item[0] >= since]
    return max(fresh)[1] if fresh else None


async def schedule_status(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    farm_id: uuid.UUID,
    crop: str | None,
    sowing_date: date | None,
    registry: CropStageRegistry = ACTIVE_CROP_STAGE_REGISTRY,
    today: date | None = None,
) -> ScheduleStatus:
    today = today or today_ist()
    status = ScheduleStatus()
    status.overdue_tasks = await _overdue_tasks(session, farm_id, today)
    if status.overdue_tasks:
        status.reasons.append("overdue_task")
    status.calendar_available, status.expected_stage = expected_generic_stage(
        registry, crop, sowing_date, today
    )
    status.observed_stage = await _observed_stage(session, user_id, farm_id)
    if is_lagging(status.expected_stage, status.observed_stage):
        status.reasons.append("stage_lagging")
    status.behind = bool(status.reasons)
    return status
