"""Growth Monitor "behind schedule": overdue organic task OR stage lag."""
from __future__ import annotations

from datetime import date, timedelta

from app.modules.auth.models import User
from app.modules.calendar.registry import ACTIVE_CROP_STAGE_REGISTRY, CropStageRegistry
from app.modules.farms.models import Farm
from app.modules.growth.models import CropStageState
from app.modules.growth.schedule_status import (
    CALENDAR_TO_GENERIC,
    expected_generic_stage,
    is_lagging,
    schedule_status,
)
from app.modules.organic_mvp.models import (
    OrganicCropCycle,
    OrganicPlot,
    OrganicScheduledTask,
    OrganicTaskTemplate,
)

TODAY = date(2026, 10, 2)


async def _farm(db_session, uid: str) -> tuple[User, Farm]:
    user = User(firebase_uid=uid, status="active")
    db_session.add(user)
    await db_session.flush()
    farm = Farm(user_id=user.id, name="Schedule field", crop="paddy")
    db_session.add(farm)
    await db_session.flush()
    return user, farm


def test_every_live_calendar_code_is_mapped_or_deliberately_skipped() -> None:
    skipped = {
        "disease_and_pest_scouting", "irrigation_management", "fertilizer_management",
        "weed_management", "year1_irrigation_and_early_care", "year2_manuring_and_intercropping",
    }
    for schedule in ACTIVE_CROP_STAGE_REGISTRY._active.values():
        for stage in schedule.stages:
            assert stage.code in CALENDAR_TO_GENERIC or stage.code in skipped, stage.code


def test_expected_stage_follows_verified_calendar_and_fails_closed() -> None:
    available, stage = expected_generic_stage(
        ACTIVE_CROP_STAGE_REGISTRY, "paddy", TODAY - timedelta(days=50), TODAY
    )
    assert available and stage == "vegetative"
    assert expected_generic_stage(CropStageRegistry([]), "paddy", TODAY, TODAY) == (False, None)
    assert expected_generic_stage(ACTIVE_CROP_STAGE_REGISTRY, "paddy", None, TODAY) == (True, None)
    assert is_lagging("flowering", "vegetative")
    assert not is_lagging("vegetative", "vegetative")
    assert not is_lagging("vegetative", "unknown")
    assert not is_lagging(None, "seedling")


async def test_on_track_farm_is_not_behind(db_session) -> None:
    user, farm = await _farm(db_session, "sched-ok")
    status = await schedule_status(
        db_session, user_id=user.id, farm_id=farm.id, crop="paddy",
        sowing_date=TODAY - timedelta(days=50), today=TODAY,
    )
    # No recent stage evidence and no tasks → no claim either way.
    assert status.behind is False and status.reasons == []
    assert status.expected_stage == "vegetative" and status.observed_stage is None


async def test_confirmed_stage_lagging_calendar_is_behind(db_session) -> None:
    user, farm = await _farm(db_session, "sched-lag")
    db_session.add(CropStageState(
        user_id=user.id, farm_id=farm.id, crop_cycle_id="c1", state="confirmed",
        confirmed_stage="seedling", calculation_version="t", evidence_snapshot={},
    ))
    await db_session.flush()
    status = await schedule_status(
        db_session, user_id=user.id, farm_id=farm.id, crop="paddy",
        sowing_date=date.today() - timedelta(days=50), today=date.today(),
    )
    assert status.behind is True
    assert status.reasons == ["stage_lagging"]
    assert (status.expected_stage, status.observed_stage) == ("vegetative", "seedling")


async def test_overdue_organic_task_is_behind(db_session) -> None:
    user, farm = await _farm(db_session, "sched-overdue")
    plot = OrganicPlot(farm_id=farm.id, name="Plot A")
    db_session.add(plot)
    await db_session.flush()
    cycle = OrganicCropCycle(plot_id=plot.id, crop_id="paddy", sowing_date=TODAY - timedelta(days=20))
    template = OrganicTaskTemplate(crop_id="paddy", district="Thanjavur", version="t1", tasks=[])
    db_session.add_all([cycle, template])
    await db_session.flush()
    for offset, task_status in ((3, "pending"), (2, "completed"), (-1, "pending")):
        db_session.add(OrganicScheduledTask(
            crop_cycle_id=cycle.id, template_id=template.id, day_offset=0,
            due_on=TODAY - timedelta(days=offset), title_ta="பணி", body_ta="விவரம்",
            status=task_status,
        ))
    await db_session.flush()
    status = await schedule_status(
        db_session, user_id=user.id, farm_id=farm.id, crop="paddy",
        sowing_date=None, today=TODAY,
    )
    assert status.overdue_tasks == 1  # only past-due AND still pending
    assert status.reasons == ["overdue_task"] and status.behind is True


async def test_schedule_status_endpoint_is_owner_only(db_session) -> None:
    import httpx
    from app.api.errors import register_exception_handlers
    from app.core.database import get_session
    from app.modules.auth.dependencies import get_current_user
    from app.modules.growth.router import router
    from fastapi import FastAPI

    owner, farm = await _farm(db_session, "sched-api-owner")
    stranger, _ = await _farm(db_session, "sched-api-other")

    def build(user):
        app = FastAPI()
        app.include_router(router)
        register_exception_handlers(app)

        async def session_override():
            yield db_session

        app.dependency_overrides[get_session] = session_override
        app.dependency_overrides[get_current_user] = lambda: user
        return app

    for user, expected in ((owner, 200), (stranger, 404)):
        transport = httpx.ASGITransport(app=build(user))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/growth/schedule-status", params={"farm_id": str(farm.id)})
        assert res.status_code == expected
    assert res.json()["error_code"] == "farm_not_found"
