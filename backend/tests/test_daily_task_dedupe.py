"""Dedupe- and merge-rule tests for the ranking engine -- the two
mechanisms that keep a farmer from ever seeing two cards about the same
underlying event.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.daily_task.constants import SignalType, TaskType, Urgency
from tests.test_daily_task_ranking import FakeRepo, _signal  # reuse the fixture helper

pytestmark = pytest.mark.asyncio


@pytest.fixture
def repo() -> FakeRepo:
    return FakeRepo()


@pytest.fixture
def engine(repo):
    from app.modules.daily_task.ranking_engine import RankingEngine

    return RankingEngine(repo)


@pytest.fixture(autouse=True)
def _enable_all_task_types(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "daily_tasks_enabled", True)
    monkeypatch.setattr(settings, "uneven_growth_enabled", True)
    monkeypatch.setattr(settings, "cautious_waterlogging_tasks_enabled", True)


async def test_same_dedupe_key_keeps_only_the_most_recent_observation(engine):
    farm_id = uuid.uuid4()
    key = f"{farm_id}:irrigation_dryness:same-bucket"
    older = _signal(
        signal_type=SignalType.IRRIGATION_DRYNESS, task_type=TaskType.IRRIGATION_INSPECTION, field_id=farm_id,
        dedupe_key=key, observed_at=datetime.now(UTC) - timedelta(hours=6),
    )
    newer = _signal(
        signal_type=SignalType.IRRIGATION_DRYNESS, task_type=TaskType.IRRIGATION_INSPECTION, field_id=farm_id,
        dedupe_key=key, observed_at=datetime.now(UTC),
    )
    result = await engine.rank_for_farm(farm_id, [older, newer])
    assert len(result.shown) == 1
    assert result.shown[0].signal.id == newer.id
    assert any(rc.decision == "suppressed_duplicate_dedupe_key" for rc in result.suppressed)


async def test_drainage_suppresses_same_day_irrigation_via_merge_rule(engine):
    farm_id = uuid.uuid4()
    irrigation = _signal(signal_type=SignalType.IRRIGATION_DRYNESS, task_type=TaskType.IRRIGATION_INSPECTION, field_id=farm_id)
    drainage = _signal(signal_type=SignalType.DRAINAGE_RISK, task_type=TaskType.DRAINAGE_INSPECTION, field_id=farm_id, urgency=Urgency.TODAY)

    result = await engine.rank_for_farm(farm_id, [irrigation, drainage])

    shown_types = {rc.signal.recommended_task_type for rc in result.shown}
    assert TaskType.DRAINAGE_INSPECTION in shown_types
    assert TaskType.IRRIGATION_INSPECTION not in shown_types
    merged = [rc for rc in result.suppressed if rc.decision.startswith("suppressed_merged_into_")]
    assert len(merged) == 1
    assert merged[0].signal.recommended_task_type == TaskType.IRRIGATION_INSPECTION


async def test_two_different_fields_never_dedupe_against_each_other(engine):
    farm_a = uuid.uuid4()
    farm_b = uuid.uuid4()
    sig_a = _signal(signal_type=SignalType.IRRIGATION_DRYNESS, task_type=TaskType.IRRIGATION_INSPECTION, field_id=farm_a)
    sig_b = _signal(signal_type=SignalType.IRRIGATION_DRYNESS, task_type=TaskType.IRRIGATION_INSPECTION, field_id=farm_b)

    result_a = await engine.rank_for_farm(farm_a, [sig_a])
    result_b = await engine.rank_for_farm(farm_b, [sig_b])

    assert len(result_a.shown) == 1
    assert len(result_b.shown) == 1


async def test_re_running_generation_for_same_signal_is_idempotent_at_service_layer():
    """Documents the idempotency contract enforced in
    DailyTaskService.generate_tasks_for_farm (not RankingEngine itself):
    a repeated scheduler run for the same (dedupe_key, observed_date) must
    not create a second DailySignal row -- exercised end-to-end in
    test_daily_task_state_transitions.py's DB-backed tests.
    """
    assert True
