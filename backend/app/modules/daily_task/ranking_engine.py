"""Layer 3 -- Ranking and Policy Engine.

Turns a list of candidate `EvidenceSignal`s for one farmer into at most
`MAX_TASKS_PER_FARMER_PER_DAY` farmer-facing tasks:

  - deduplication (by dedupe_key)
  - policy gating (feature flags, disabled task types, the flood-claim guard)
  - cooldown/suppression (per-field, per-task-type response history)
  - ranking (tier -> urgency window -> confidence -> cost-of-inaction)
  - the hard 2-per-day cap
  - a full audit trail via `DailyTaskAuditLog` for every candidate's fate.

Nothing here computes agronomic truth -- it only decides which
already-computed signals a farmer sees today, and in what order. Copy
generation is a separate step (task_copy.py / service.py).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.modules.daily_task.constants import (
    MAX_TASKS_PER_FARMER_PER_DAY,
    TASK_COOLDOWN_DAYS_DEFAULT,
    TASK_COOLDOWN_DAYS_NOT_RELEVANT,
    TASK_COOLDOWN_DAYS_NO_ISSUE,
    TASK_TIER,
    Confidence,
    TaskType,
    Urgency,
    is_task_type_enabled,
)
from app.modules.daily_task.repository import DailyTaskRepository
from app.modules.daily_task.schemas import EvidenceSignal

_URGENCY_ORDER = {
    Urgency.TODAY: 1,
    Urgency.WITHIN_48H: 2,
    Urgency.BEFORE_RAIN: 3,
    Urgency.THIS_WEEK: 4,
}

_CONFIDENCE_SCORE = {Confidence.HIGH: 1.0, Confidence.MEDIUM: 0.6, Confidence.LOW: 0.3}

_COST_OF_INACTION_WEIGHT = {
    TaskType.DRAINAGE_INSPECTION: 1.0,
    TaskType.IRRIGATION_INSPECTION: 0.8,
    TaskType.SOWING_GERMINATION_CHECK: 0.6,
    TaskType.UNEVEN_GROWTH_INSPECTION: 0.4,
    TaskType.EVIDENCE_PACK_TRIGGER: 0.0,  # never ranked against the daily cap
}

# When both fire the same day for the same field, only the winner is shown;
# the loser is suppressed-by-merge rather than competing on score -- heavy
# rain firing a drainage-inspection signal makes an irrigation-dryness signal
# for the same field moot the same day (the field is already wet).
_MERGE_PRIORITY_OVER: dict[TaskType, list[TaskType]] = {
    TaskType.DRAINAGE_INSPECTION: [TaskType.IRRIGATION_INSPECTION],
}


@dataclass
class RankedCandidate:
    signal: EvidenceSignal
    rank_score: float
    tier: int
    decision: str  # "shown" | "suppressed_<reason>"
    decision_detail: dict = field(default_factory=dict)


@dataclass
class RankingResult:
    run_id: uuid.UUID
    farm_id: uuid.UUID
    shown: list[RankedCandidate]
    suppressed: list[RankedCandidate]


class RankingEngine:
    def __init__(self, repo: DailyTaskRepository) -> None:
        self._repo = repo

    async def rank_for_farm(
        self, farm_id: uuid.UUID, candidates: list[EvidenceSignal], *, now: datetime | None = None
    ) -> RankingResult:
        now = now or datetime.now(UTC)
        run_id = uuid.uuid4()
        results: list[RankedCandidate] = []

        # --- Gate A: feature flags + policy -------------------------------
        gated: list[EvidenceSignal] = []
        for sig in candidates:
            if not is_task_type_enabled(sig.recommended_task_type):
                results.append(self._suppressed(sig, "feature_flag_disabled", tier=self._tier(sig)))
                continue
            if sig.valid_until <= now:
                results.append(self._suppressed(sig, "expired_before_ranking", tier=self._tier(sig)))
                continue
            if "waterlogging_unconfirmed_flood_claim" in sig.policy_flags:
                # Defensive only -- providers must never set this flag, but if
                # one ever does, the engine refuses to rank the signal at all
                # rather than let a stricter claim slip through.
                results.append(
                    self._suppressed(sig, "policy_blocked_definitive_flood_claim", tier=self._tier(sig))
                )
                continue
            gated.append(sig)

        # --- Gate B: per-field dedupe by dedupe_key ------------------------
        deduped: dict[str, EvidenceSignal] = {}
        for sig in gated:
            existing = deduped.get(sig.dedupe_key)
            if existing is None or sig.observed_at > existing.observed_at:
                if existing is not None:
                    results.append(self._suppressed(existing, "duplicate_dedupe_key", tier=self._tier(existing)))
                deduped[sig.dedupe_key] = sig
            else:
                results.append(self._suppressed(sig, "duplicate_dedupe_key", tier=self._tier(sig)))
        working = list(deduped.values())

        # --- Gate C: same-day merge rules -----------------------------------
        working = self._apply_merge_rules(working, results)

        # --- Gate D: cooldown / suppression from farmer response history ---
        survivors: list[EvidenceSignal] = []
        for sig in working:
            cooldown_reason = await self._check_cooldown(farm_id, sig, now)
            if cooldown_reason:
                results.append(self._suppressed(sig, cooldown_reason, tier=self._tier(sig)))
                continue
            survivors.append(sig)

        # --- Score + sort ---------------------------------------------------
        scored = [self._score(sig) for sig in survivors]
        scored.sort(key=lambda rc: rc.rank_score, reverse=True)

        # --- Gate E: hard cap -------------------------------------------------
        shown = [rc for rc in scored if rc.tier > 0][:MAX_TASKS_PER_FARMER_PER_DAY]
        # Evidence-pack-trigger signals (tier 0) are farmer/event-initiated,
        # never subject to the daily ranking cap.
        shown += [rc for rc in scored if rc.tier == 0]
        for rc in shown:
            rc.decision = "shown"
        cut = [rc for rc in scored if rc not in shown]
        for rc in cut:
            rc.decision = "suppressed_daily_cap"
        results.extend(shown)
        results.extend(cut)

        await self._repo.write_audit_log(
            run_id=run_id,
            farm_id=farm_id,
            entries=[
                {
                    "signal_id": str(rc.signal.id),
                    "signal_type": rc.signal.signal_type.value,
                    "decision": rc.decision,
                    "decision_detail": {"rank_score": rc.rank_score, **rc.decision_detail},
                }
                for rc in results
            ],
        )

        return RankingResult(
            run_id=run_id,
            farm_id=farm_id,
            shown=[rc for rc in results if rc.decision == "shown"],
            suppressed=[rc for rc in results if rc.decision != "shown"],
        )

    # ------------------------------------------------------------------ #
    def _tier(self, sig: EvidenceSignal) -> int:
        return TASK_TIER.get(sig.recommended_task_type, 3)

    def _suppressed(self, sig: EvidenceSignal, reason: str, *, tier: int) -> RankedCandidate:
        return RankedCandidate(signal=sig, rank_score=0.0, tier=tier, decision=f"suppressed_{reason}")

    def _apply_merge_rules(
        self, signals: list[EvidenceSignal], results: list[RankedCandidate]
    ) -> list[EvidenceSignal]:
        by_type: dict[TaskType, EvidenceSignal] = {s.recommended_task_type: s for s in signals}
        drop: set[TaskType] = set()
        for winner_type, losers in _MERGE_PRIORITY_OVER.items():
            if winner_type in by_type:
                for loser_type in losers:
                    if loser_type in by_type and loser_type not in drop:
                        drop.add(loser_type)
                        results.append(
                            self._suppressed(
                                by_type[loser_type],
                                "merged_into_" + winner_type.value,
                                tier=self._tier(by_type[loser_type]),
                            )
                        )
        return [s for s in signals if s.recommended_task_type not in drop]

    async def _check_cooldown(self, farm_id: uuid.UUID, sig: EvidenceSignal, now: datetime) -> str | None:
        last = await self._repo.get_last_task_for_field_and_type(farm_id, sig.recommended_task_type)
        if last is None:
            return None
        last_response = await self._repo.get_final_response(last.id)
        if last_response is None:
            return None  # no farmer response recorded yet -- don't double-suppress an unresolved task
        if last_response == "not_relevant":
            cooldown_days = TASK_COOLDOWN_DAYS_NOT_RELEVANT
        elif last_response == "no_issue":
            cooldown_days = TASK_COOLDOWN_DAYS_NO_ISSUE
        else:
            cooldown_days = TASK_COOLDOWN_DAYS_DEFAULT
        if now - last.created_at < timedelta(days=cooldown_days):
            if last_response == "problem_found" and now - last.created_at >= timedelta(
                days=cooldown_days / 2
            ):
                return None
            return f"cooldown_{last_response}"
        return None

    def _score(self, sig: EvidenceSignal) -> RankedCandidate:
        tier = self._tier(sig)
        tier_component = (4 - tier) * 100.0
        urgency_component = (5 - _URGENCY_ORDER.get(sig.urgency, 4)) * 10.0
        confidence_component = _CONFIDENCE_SCORE.get(sig.confidence, 0.3) * 5.0
        cost_component = _COST_OF_INACTION_WEIGHT.get(sig.recommended_task_type, 0.2) * 3.0
        score = tier_component + urgency_component + confidence_component + cost_component
        return RankedCandidate(
            signal=sig,
            rank_score=score,
            tier=tier,
            decision="pending",
            decision_detail={
                "tier_component": tier_component,
                "urgency_component": urgency_component,
                "confidence_component": confidence_component,
                "cost_component": cost_component,
            },
        )
