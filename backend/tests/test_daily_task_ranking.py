"""Ranking engine unit tests -- pure decision logic exercised against an
in-memory fake repository, mirroring the style of `tests/test_jobs.py`
(fast, no DB needed beyond the fake for the audit-log write).
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.daily_task.constants import (
    Confidence,
    MAX_TASKS_PER_FARMER_PER_DAY,
    Severity,
    SignalType,
    SourceModule,
    TaskType,
    Urgency,
)
from app.modules.daily_task.ranking_engine import RankingEngine
from app.modules.daily_task.schemas import EvidenceSignal

pytestmark = pytest.mark.asyncio


def _signal(
    *,
    signal_type: SignalType,
    task_type: TaskType,
    urgency: Urgency = Urgency.WITHIN_48H,
    confidence: Confidence = Confidence.MEDIUM,
    field_id=None,
    observed_at=None,
    dedupe_key=None,
) -> EvidenceSignal:
    now = observed_at or datetime.now(UTC)
    field_id = field_id or uuid.uuid4()
    return EvidenceSignal(
        farmer_id=uuid.uuid4(),
        field_id=field_id,
        signal_type=signal_type,
        source_module=SourceModule.SATELLITE,
        observed_at=now,
        valid_until=now + timedelta(hours=48),
        confidence=confidence,
        severity=Severity.ATTENTION,
        urgency=urgency,
        recommended_task_type=task_type,
        dedupe_key=dedupe_key or f"{field_id}:{signal_type.value}:{now.date()}",
    )


class FakeRepo:
    """Minimal stand-in for DailyTaskRepository -- only the methods
    RankingEngine actually calls.
    """

    def __init__(self) -> None:
        self.audit_entries: list[dict] = []
        self.last_task_by_field_type: dict = {}
        self.final_response_by_task: dict = {}

    async def get_last_task_for_field_and_type(self, farm_id, task_type):
        return self.last_task_by_field_type.get((farm_id, task_type))

    async def get_final_response(self, task_id):
        return self.final_response_by_task.get(task_id)

    async def write_audit_log(self, *, run_id, farm_id, entries):
        self.audit_entries.extend(entries)


@pytest.fixture
def repo() -> FakeRepo:
    return FakeRepo()


@pytest.fixture
def engine(repo) -> RankingEngine:
    return RankingEngine(repo)


@pytest.fixture(autouse=True)
def _enable_all_task_types(monkeypatch):
    """Ranking-logic tests exercise gates other than the feature-flag gate
    by default -- flip every MVP flag on so the flag gate never interferes,
    except where a test explicitly wants it off.
    """
    from app.core.config import settings

    monkeypatch.setattr(settings, "daily_tasks_enabled", True)
    monkeypatch.setattr(settings, "uneven_growth_enabled", True)
    monkeypatch.setattr(settings, "cautious_waterlogging_tasks_enabled", True)


async def test_caps_at_two_tasks_per_day_even_with_more_candidates(engine):
    farm_id = uuid.uuid4()
    candidates = [
        _signal(signal_type=SignalType.IRRIGATION_DRYNESS, task_type=TaskType.IRRIGATION_INSPECTION, field_id=farm_id),
        _signal(signal_type=SignalType.SOWING_GERMINATION_DELAY, task_type=TaskType.SOWING_GERMINATION_CHECK, field_id=farm_id),
        _signal(signal_type=SignalType.UNEVEN_GROWTH_ZONE, task_type=TaskType.UNEVEN_GROWTH_INSPECTION, field_id=farm_id, urgency=Urgency.THIS_WEEK),
    ]
    result = await engine.rank_for_farm(farm_id, candidates)
    assert len(result.shown) == MAX_TASKS_PER_FARMER_PER_DAY
    assert any(rc.decision == "suppressed_daily_cap" for rc in result.suppressed)


async def test_drainage_tier_1_always_outranks_irrigation_tier_2(engine):
    farm_id = uuid.uuid4()
    drainage = _signal(signal_type=SignalType.DRAINAGE_RISK, task_type=TaskType.DRAINAGE_INSPECTION, field_id=farm_id, urgency=Urgency.TODAY, confidence=Confidence.LOW)
    sowing = _signal(signal_type=SignalType.SOWING_GERMINATION_DELAY, task_type=TaskType.SOWING_GERMINATION_CHECK, field_id=farm_id, confidence=Confidence.HIGH)

    result = await engine.rank_for_farm(farm_id, [drainage, sowing])

    shown_types = [rc.signal.recommended_task_type for rc in result.shown]
    assert TaskType.DRAINAGE_INSPECTION in shown_types
    # Drainage's low confidence still beats sowing's high confidence, because
    # tier dominates every other ranking factor.
    assert shown_types[0] == TaskType.DRAINAGE_INSPECTION


async def test_feature_flagged_off_task_type_never_shown(engine, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "uneven_growth_enabled", False)
    farm_id = uuid.uuid4()
    signal = _signal(signal_type=SignalType.UNEVEN_GROWTH_ZONE, task_type=TaskType.UNEVEN_GROWTH_INSPECTION, field_id=farm_id)
    result = await engine.rank_for_farm(farm_id, [signal])
    assert result.shown == []
    assert result.suppressed[0].decision == "suppressed_feature_flag_disabled"


async def test_expired_signal_is_suppressed_not_shown(engine):
    farm_id = uuid.uuid4()
    stale = _signal(
        signal_type=SignalType.IRRIGATION_DRYNESS,
        task_type=TaskType.IRRIGATION_INSPECTION,
        field_id=farm_id,
        observed_at=datetime.now(UTC) - timedelta(days=5),
    )
    stale = stale.model_copy(update={"valid_until": datetime.now(UTC) - timedelta(hours=1)})
    result = await engine.rank_for_farm(farm_id, [stale])
    assert result.shown == []
    assert result.suppressed[0].decision == "suppressed_expired_before_ranking"


async def test_no_issue_response_suppresses_same_task_type_within_cooldown(engine, repo):
    farm_id = uuid.uuid4()
    task_type = TaskType.IRRIGATION_INSPECTION
    fake_task = type("T", (), {"id": uuid.uuid4(), "created_at": datetime.now(UTC) - timedelta(days=1)})()
    repo.last_task_by_field_type[(farm_id, task_type)] = fake_task
    repo.final_response_by_task[fake_task.id] = "no_issue"

    signal = _signal(signal_type=SignalType.IRRIGATION_DRYNESS, task_type=task_type, field_id=farm_id)
    result = await engine.rank_for_farm(farm_id, [signal])

    assert result.shown == []
    assert result.suppressed[0].decision == "suppressed_cooldown_no_issue"


async def test_audit_log_written_for_every_candidate_including_suppressed(engine, repo, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "uneven_growth_enabled", False)
    farm_id = uuid.uuid4()
    candidates = [
        _signal(signal_type=SignalType.IRRIGATION_DRYNESS, task_type=TaskType.IRRIGATION_INSPECTION, field_id=farm_id),
        _signal(signal_type=SignalType.UNEVEN_GROWTH_ZONE, task_type=TaskType.UNEVEN_GROWTH_INSPECTION, field_id=farm_id),
    ]
    await engine.rank_for_farm(farm_id, candidates)
    assert len(repo.audit_entries) == len(candidates)
    assert all("decision" in entry and "decision_detail" in entry for entry in repo.audit_entries)
