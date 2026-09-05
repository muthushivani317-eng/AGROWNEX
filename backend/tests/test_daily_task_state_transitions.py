"""Task state-transition tests -- run against the real DB session fixture
(`db_session`, the same fixture used throughout `tests/test_jobs.py`) since
these exercise DailyTaskService + DailyTaskRepository together, not just
in-memory logic.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.daily_task.constants import ResponseType, TaskStatus, TaskType
from app.modules.daily_task.exceptions import TaskAlreadyClosedError, TaskNotFoundError
from app.modules.daily_task.models import DailySignal, DailyTask
from app.modules.daily_task.repository import DailyTaskRepository
from app.modules.daily_task.schemas import TaskRespondRequest
from app.modules.daily_task.service import DailyTaskService

pytestmark = pytest.mark.asyncio


async def _make_active_task(db_session, *, farm_id=None, user_id=None) -> DailyTask:
    farm_id = farm_id or uuid.uuid4()
    user_id = user_id or uuid.uuid4()
    signal = DailySignal(
        id=uuid.uuid4(), farm_id=farm_id, user_id=user_id, signal_type="irrigation_dryness",
        source_module="satellite", observed_at=datetime.now(UTC), valid_until=datetime.now(UTC) + timedelta(hours=48),
        confidence="medium", severity="attention", urgency="within_48h",
        recommended_task_type="irrigation_inspection", dedupe_key=str(uuid.uuid4()), status="ranked_shown",
    )
    db_session.add(signal)
    await db_session.flush()
    task = DailyTask(
        id=uuid.uuid4(), farm_id=farm_id, user_id=user_id, signal_id=signal.id, merged_signal_ids=[],
        task_type=TaskType.IRRIGATION_INSPECTION.value, tier=2, rank_position=1,
        title_ta="இன்றைய பண்ணை செயல்", task_text_ta="நீர்ப்பாசனத்தை பாருங்கள்.", reason_text_ta="வறண்டு வருகிறது.",
        why_am_i_seeing_this_ta="...", field_label="South field", urgency="within_48h",
        status=TaskStatus.ACTIVE.value, valid_until=datetime.now(UTC) + timedelta(hours=48),
    )
    db_session.add(task)
    await db_session.flush()
    return task


def _service(db_session) -> DailyTaskService:
    repo = DailyTaskRepository(db_session)
    return DailyTaskService(repo, providers=[], ranking_engine=None, evidence_pack_service=None)


async def test_active_task_transitions_to_responded_on_done(db_session):
    task = await _make_active_task(db_session)
    service = _service(db_session)

    response = await service.respond_to_task(task.id, TaskRespondRequest(response_type=ResponseType.DONE))

    assert response.status == TaskStatus.RESPONDED
    assert response.escalated is False
    refreshed = await DailyTaskRepository(db_session).get_task(task.id)
    assert refreshed.status == TaskStatus.RESPONDED.value


async def test_problem_found_marks_task_escalated_and_prompts_media(db_session):
    task = await _make_active_task(db_session)
    service = _service(db_session)

    response = await service.respond_to_task(task.id, TaskRespondRequest(response_type=ResponseType.PROBLEM_FOUND))

    assert response.escalated is True
    assert response.follow_up_prompt in ("photo_voice_optional", "photo_voice_encouraged")


async def test_responding_twice_raises_task_already_closed(db_session):
    task = await _make_active_task(db_session)
    service = _service(db_session)

    await service.respond_to_task(task.id, TaskRespondRequest(response_type=ResponseType.NO_ISSUE))

    with pytest.raises(TaskAlreadyClosedError):
        await service.respond_to_task(task.id, TaskRespondRequest(response_type=ResponseType.DONE))


async def test_snoozing_moves_task_to_snoozed_status_with_a_future_time(db_session):
    task = await _make_active_task(db_session)
    service = _service(db_session)

    await service.snooze_task(task.id, "later_today")

    refreshed = await DailyTaskRepository(db_session).get_task(task.id)
    assert refreshed.status == TaskStatus.SNOOZED.value
    assert refreshed.snoozed_until > datetime.now(UTC)


async def test_responding_to_unknown_task_raises_not_found(db_session):
    service = _service(db_session)

    with pytest.raises(TaskNotFoundError):
        await service.respond_to_task(uuid.uuid4(), TaskRespondRequest(response_type=ResponseType.DONE))


async def test_stale_active_task_is_expired_by_sweep(db_session):
    task = await _make_active_task(db_session)
    repo = DailyTaskRepository(db_session)
    await db_session.execute(
        DailyTask.__table__.update().where(DailyTask.id == task.id).values(valid_until=datetime.now(UTC) - timedelta(hours=1))
    )
    expired_count = await repo.expire_stale_active_tasks(now=datetime.now(UTC))
    assert expired_count == 1
    # The Core-level UPDATE above bypasses the ORM identity map, so the
    # already-loaded `task` instance must be refreshed before a re-SELECT
    # picks up the new column value (a fresh request in production always
    # gets a fresh session, so this is a test-only concern).
    await db_session.refresh(task)
    refreshed = await repo.get_task(task.id)
    assert refreshed.status == TaskStatus.EXPIRED.value


async def test_generate_tasks_for_farm_is_idempotent_for_same_dedupe_key_and_day(db_session, monkeypatch):
    """The service-layer idempotency contract: re-running generation for the
    same (dedupe_key, observed_date) must not create a second DailySignal
    row (a scheduler retry must not duplicate a candidate for the same
    real-world event).
    """
    from app.modules.daily_task.constants import (
        Confidence,
        Severity,
        SignalType,
        SourceModule,
        TaskType as TT,
        Urgency,
    )
    from app.modules.daily_task.schemas import EvidenceSignal

    from app.core.config import settings

    monkeypatch.setattr(settings, "daily_tasks_enabled", True)
    farm_id = uuid.uuid4()
    owner_user_id = uuid.uuid4()
    now = datetime.now(UTC)
    dedupe_key = f"{farm_id}:irrigation_dryness:{now.date()}"

    class _FakeFarm:
        id = farm_id
        user_id = owner_user_id
        name = "Test Farm"

    class _OneShotProvider:
        async def collect(self, user, farm):
            return [
                EvidenceSignal(
                    farmer_id=farm.user_id,
                    field_id=farm.id,
                    signal_type=SignalType.IRRIGATION_DRYNESS,
                    source_module=SourceModule.SATELLITE,
                    observed_at=now,
                    valid_until=now + timedelta(hours=48),
                    confidence=Confidence.MEDIUM,
                    severity=Severity.ATTENTION,
                    urgency=Urgency.WITHIN_48H,
                    recommended_task_type=TT.IRRIGATION_INSPECTION,
                    dedupe_key=dedupe_key,
                )
            ]

    from app.modules.daily_task.ranking_engine import RankingEngine

    repo = DailyTaskRepository(db_session)
    service = DailyTaskService(repo, providers=[_OneShotProvider()], ranking_engine=RankingEngine(repo), evidence_pack_service=None)

    class _FakeUser:
        id = owner_user_id

    await service.generate_tasks_for_farm(_FakeUser(), _FakeFarm(), now=now)
    await service.generate_tasks_for_farm(_FakeUser(), _FakeFarm(), now=now)  # scheduler retry

    from sqlalchemy import select

    result = await db_session.execute(select(DailySignal).where(DailySignal.dedupe_key == dedupe_key))
    signals = result.scalars().all()
    assert len(signals) == 1

    # The regression this guards: EvidenceSignal.id is a fresh uuid4() every
    # time a provider's collect() runs (see signal_providers.py -- no
    # provider sets `id=` explicitly), so the *second* generate call's
    # candidate carries an id that was never persisted. If the service ever
    # ranks that second-run candidate into a shown task using its own
    # (unpersisted) id rather than the already-persisted `existing.id`, the
    # created DailyTask.signal_id points at a DailySignal row that doesn't
    # exist -- silently tolerated by this suite's SQLite fixture (FK
    # enforcement is off), but a real daily_tasks_signal_id_fkey
    # IntegrityError against the real Postgres schema. Assert the referential
    # link explicitly so this suite catches it even without FK enforcement.
    tasks_result = await db_session.execute(select(DailyTask).where(DailyTask.farm_id == farm_id))
    tasks = tasks_result.scalars().all()
    assert len(tasks) == 1
    assert tasks[0].signal_id == signals[0].id
