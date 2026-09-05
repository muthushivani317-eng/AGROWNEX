"""Orchestration service -- wires Layers 1 through 4 together. Both `jobs.py`
(the overnight batch) and `router.py` (any on-demand action) call into this
one object. No FastAPI or ARQ types appear here, so it stays unit-testable.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.modules.auth.models import User
from app.modules.daily_task.constants import ResponseType, TaskStatus, TaskType
from app.modules.daily_task.evidence_pack import EvidencePackService
from app.modules.daily_task.exceptions import TaskAlreadyClosedError, TaskNotFoundError
from app.modules.daily_task.ranking_engine import RankingEngine, RankingResult
from app.modules.daily_task.repository import DailyTaskRepository
from app.modules.daily_task.schemas import EvidenceSignal, TaskRespondRequest, TaskRespondResponse
from app.modules.daily_task.signal_providers import SignalProvider
from app.modules.daily_task.task_copy import render_task_copy
from app.modules.farms.models import Farm


def _field_label(farm: Farm) -> str | None:
    """A short, farmer-recognizable label for the task card -- the farm's own
    name if the farmer named it, else its village (see `Farm.name`,
    `FarmLocation.village` in `app/modules/farms/models.py`). Never a raw
    farm id or a technical identifier.
    """
    if farm.name:
        return farm.name
    location = getattr(farm, "location", None)
    if location is not None and location.village:
        return location.village
    return None


class DailyTaskService:
    def __init__(
        self,
        repo: DailyTaskRepository,
        providers: list[SignalProvider],
        ranking_engine: RankingEngine,
        evidence_pack_service: EvidencePackService,
    ) -> None:
        self._repo = repo
        self._providers = providers
        self._ranking = ranking_engine
        self._evidence_pack = evidence_pack_service

    # ------------------------------------------------------------------ #
    # Daily generation (called by jobs.py, once per active farm per day)
    # ------------------------------------------------------------------ #
    async def generate_tasks_for_farm(
        self, user: User, farm: Farm, *, now: datetime | None = None
    ) -> RankingResult:
        now = now or datetime.now(UTC)

        candidates: list[EvidenceSignal] = []
        for provider in self._providers:
            candidates.extend(await provider.collect(user, farm))

        # Persist every candidate as a DailySignal row FIRST (status=candidate)
        # so the audit trail is complete even for signals the ranking engine
        # immediately suppresses.
        persisted: list[EvidenceSignal] = []
        for candidate in candidates:
            existing = await self._repo.get_signal_by_dedupe_key_and_date(
                candidate.dedupe_key, candidate.observed_at.date()
            )
            if existing is not None:
                # Idempotency: re-running generation for the same farm/day
                # (a scheduler retry) must never create a second row for the
                # same real-world event.
                persisted.append(candidate)
                continue
            await self._repo.create_signal(
                id=candidate.id,
                farm_id=candidate.field_id,
                user_id=candidate.farmer_id,
                signal_type=candidate.signal_type.value,
                source_module=candidate.source_module.value,
                observed_at=candidate.observed_at,
                valid_until=candidate.valid_until,
                confidence=candidate.confidence.value,
                severity=candidate.severity.value,
                urgency=candidate.urgency.value,
                evidence_summary=candidate.evidence_summary,
                evidence_technical=candidate.evidence_technical,
                evidence_refs=candidate.evidence_refs,
                policy_flags=candidate.policy_flags,
                recommended_task_type=candidate.recommended_task_type.value,
                dedupe_key=candidate.dedupe_key,
                status="candidate",
            )
            persisted.append(candidate)

        result = await self._ranking.rank_for_farm(farm.id, persisted, now=now)
        field_label = _field_label(farm)

        for position, ranked in enumerate(
            sorted(result.shown, key=lambda rc: rc.rank_score, reverse=True), start=1
        ):
            copy = render_task_copy(ranked.signal)
            await self._repo.create_task(
                farm_id=farm.id,
                user_id=farm.user_id,
                signal_id=ranked.signal.id,
                merged_signal_ids=[],
                task_type=ranked.signal.recommended_task_type.value,
                tier=ranked.tier,
                rank_position=position,
                title_ta=copy.title_ta,
                task_text_ta=copy.task_text_ta,
                reason_text_ta=copy.reason_text_ta,
                why_am_i_seeing_this_ta=copy.why_am_i_seeing_this_ta,
                field_label=field_label,
                urgency=copy.urgency.value,
                status=TaskStatus.ACTIVE.value,
                valid_until=ranked.signal.valid_until,
            )
            await self._repo.update_signal_status(ranked.signal.id, status="ranked_shown")

        for ranked in result.suppressed:
            await self._repo.update_signal_status(
                ranked.signal.id, status=ranked.decision, status_reason=ranked.decision
            )

        return result

    # ------------------------------------------------------------------ #
    # Farmer-facing responses
    # ------------------------------------------------------------------ #
    async def respond_to_task(self, task_id: uuid.UUID, request: TaskRespondRequest) -> TaskRespondResponse:
        task = await self._repo.get_task(task_id)
        if task is None:
            raise TaskNotFoundError(str(task_id))
        if task.status not in (TaskStatus.ACTIVE.value, TaskStatus.SNOOZED.value):
            raise TaskAlreadyClosedError(str(task_id))

        await self._repo.add_response(
            task_id=task_id,
            response_type=request.response_type.value,
            note_text=request.note_text,
        )
        await self._repo.update_task_status(task_id, TaskStatus.RESPONDED)

        follow_up = "none"
        escalated = False
        if request.response_type in (ResponseType.PROBLEM_FOUND, ResponseType.NEED_HELP):
            follow_up = (
                "photo_voice_encouraged"
                if task.task_type == TaskType.UNEVEN_GROWTH_INSPECTION.value
                else "photo_voice_optional"
            )
            escalated = True  # actual FPO routing is a Phase-2 escalation queue, not built at MVP

        return TaskRespondResponse(
            task_id=task_id, status=TaskStatus.RESPONDED, follow_up_prompt=follow_up, escalated=escalated
        )

    async def snooze_task(self, task_id: uuid.UUID, snooze_until: str) -> None:
        task = await self._repo.get_task(task_id)
        if task is None:
            raise TaskNotFoundError(str(task_id))
        delta = timedelta(hours=6) if snooze_until == "later_today" else timedelta(hours=18)
        await self._repo.update_task_status(
            task_id, TaskStatus.SNOOZED, snoozed_until=datetime.now(UTC) + delta
        )
