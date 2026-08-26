from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.farms.repositories import FarmRepository
from app.modules.growth.models import CropStageState
from app.modules.produce.harvest_readiness import ReadinessEvidence, assess_readiness
from app.modules.produce.harvest_readiness_registry import (
    ACTIVE_HARVEST_READINESS_REGISTRY,
    HarvestReadinessRegistry,
)
from app.modules.produce.models import HarvestReadinessHistory, HarvestReadinessRecord


class HarvestReadinessService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        registry: HarvestReadinessRegistry | None = None,
    ) -> None:
        self.session = session
        self.farms = FarmRepository(session)
        self.registry = registry or ACTIVE_HARVEST_READINESS_REGISTRY

    async def _farm(self, user: User, farm_id: uuid.UUID):
        farm = await self.farms.get_for_user(farm_id, user.id)
        if farm is None:
            raise PermissionError("FARM_NOT_OWNED")
        return farm

    async def current(
        self, user: User, farm_id: uuid.UUID, crop_cycle_id: str
    ) -> HarvestReadinessRecord | None:
        await self._farm(user, farm_id)
        result = await self.session.execute(
            select(HarvestReadinessRecord).where(
                HarvestReadinessRecord.user_id == user.id,
                HarvestReadinessRecord.farm_id == farm_id,
                HarvestReadinessRecord.crop_cycle_id == crop_cycle_id,
                HarvestReadinessRecord.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def evaluate(
        self,
        user: User,
        *,
        farm_id: uuid.UUID,
        crop_cycle_id: str,
        observations: tuple[str, ...],
        weather_freshness: str,
        idempotency_key: str,
    ) -> HarvestReadinessRecord:
        farm = await self._farm(user, farm_id)
        prior_event = (
            await self.session.execute(
                select(HarvestReadinessHistory).where(
                    HarvestReadinessHistory.user_id == user.id,
                    HarvestReadinessHistory.idempotency_key == idempotency_key,
                )
            )
        ).scalar_one_or_none()
        if prior_event:
            return await self.session.get(HarvestReadinessRecord, prior_event.record_id)

        stage = (
            await self.session.execute(
                select(CropStageState).where(
                    CropStageState.user_id == user.id,
                    CropStageState.farm_id == farm_id,
                    CropStageState.crop_cycle_id == crop_cycle_id,
                    CropStageState.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        criteria = self.registry.resolve(farm.crop)
        evidence = ReadinessEvidence(
            crop=farm.crop or "",
            stage=stage.confirmed_stage if stage else None,
            stage_confirmed=bool(
                stage and stage.state in {"confirmed", "corrected"} and stage.confirmed_stage
            ),
            observations=observations,
            weather_freshness=weather_freshness,
            planting_date_present=farm.sowing_date is not None,
        )
        assessment = assess_readiness(evidence, criteria)
        snapshot = {
            "crop": farm.crop,
            "planting_date_present": evidence.planting_date_present,
            "stage": evidence.stage,
            "stage_confirmed": evidence.stage_confirmed,
            "weather_freshness": weather_freshness,
            "farmer_observations": list(observations),
            "evidence_observed": list(assessment.evidence_observed),
            "missing": list(assessment.missing),
            "conflicts": list(assessment.conflicts),
            "reliability": assessment.reliability,
            "farmer_confirmation_required": assessment.farmer_confirmation_required,
            "rule_verification_status": "verified" if criteria else "unavailable",
        }
        row = await self.current(user, farm_id, crop_cycle_id)
        prior_state = row.state if row else None
        if row is None:
            row = HarvestReadinessRecord(
                user_id=user.id,
                farm_id=farm_id,
                crop_cycle_id=crop_cycle_id,
                state=assessment.state.value,
                version=1,
                criteria_version=criteria.version if criteria else None,
                criteria_hash=criteria.criteria_hash if criteria else None,
                evidence_snapshot=snapshot,
                pending_sync=False,
            )
            self.session.add(row)
            await self.session.flush()
        else:
            row.state = assessment.state.value
            row.version += 1
            row.criteria_version = criteria.version if criteria else None
            row.criteria_hash = criteria.criteria_hash if criteria else None
            row.evidence_snapshot = snapshot
        self.session.add(
            HarvestReadinessHistory(
                record_id=row.id,
                user_id=user.id,
                event="evaluate",
                prior_state=prior_state,
                next_state=row.state,
                idempotency_key=idempotency_key,
                evidence_snapshot=snapshot,
                farmer_confirmed=False,
            )
        )
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def history(self, user: User, record_id: uuid.UUID) -> list[HarvestReadinessHistory]:
        record = await self.session.get(HarvestReadinessRecord, record_id)
        if record is None or record.user_id != user.id:
            return []
        result = await self.session.execute(
            select(HarvestReadinessHistory)
            .where(HarvestReadinessHistory.record_id == record_id)
            .order_by(HarvestReadinessHistory.created_at)
        )
        return list(result.scalars())

    async def confirm(
        self,
        user: User,
        *,
        record_id: uuid.UUID,
        ready: bool,
        idempotency_key: str,
        note: str | None = None,
    ) -> HarvestReadinessRecord:
        row = await self.session.get(HarvestReadinessRecord, record_id)
        if row is None or row.user_id != user.id:
            raise PermissionError("HARVEST_READINESS_NOT_OWNED")
        existing = (
            await self.session.execute(
                select(HarvestReadinessHistory).where(
                    HarvestReadinessHistory.user_id == user.id,
                    HarvestReadinessHistory.idempotency_key == idempotency_key,
                )
            )
        ).scalar_one_or_none()
        if existing:
            return row
        if row.state != "awaiting_farmer_confirmation":
            raise ValueError("READINESS_NOT_AWAITING_CONFIRMATION")
        prior = row.state
        row.state = "farmer_confirmed_ready" if ready else "farmer_confirmed_not_ready"
        row.version += 1
        self.session.add(
            HarvestReadinessHistory(
                record_id=row.id,
                user_id=user.id,
                event="farmer_confirm",
                prior_state=prior,
                next_state=row.state,
                note=note,
                idempotency_key=idempotency_key,
                evidence_snapshot={
                    **row.evidence_snapshot,
                    "farmer_reported_ready": ready,
                },
                farmer_confirmed=True,
            )
        )
        await self.session.flush()
        await self.session.refresh(row)
        return row
