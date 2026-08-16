from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.calendar.registry import ACTIVE_CROP_STAGE_REGISTRY, CropStageRegistry
from app.modules.farms.repositories import FarmRepository
from app.modules.growth.models import CropStageState, CropStageTransition
from app.modules.growth.stage_tracking import StageEvidence, StageState, transition_stage

CALCULATION_VERSION = "stage-state-machine-v1"


class StageConflictError(ValueError):
    pass


class StageTrackingService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        stage_registry: CropStageRegistry | None = None,
    ) -> None:
        self.session = session
        self.farms = FarmRepository(session)
        self.stage_registry = stage_registry or ACTIVE_CROP_STAGE_REGISTRY

    async def _owned_farm(self, user: User, farm_id: uuid.UUID) -> None:
        if await self.farms.get_for_user(farm_id, user.id) is None:
            raise PermissionError("FARM_NOT_OWNED")

    async def current(
        self, user: User, farm_id: uuid.UUID, crop_cycle_id: str
    ) -> CropStageState | None:
        await self._owned_farm(user, farm_id)
        stmt = select(CropStageState).where(
            CropStageState.user_id == user.id,
            CropStageState.farm_id == farm_id,
            CropStageState.crop_cycle_id == crop_cycle_id,
            CropStageState.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def apply(
        self,
        user: User,
        *,
        farm_id: uuid.UUID,
        crop_cycle_id: str,
        event: str,
        stage: str | None,
        expected_version: int | None,
        idempotency_key: str,
        evidence: StageEvidence,
        reason: str | None = None,
        photo_reference: str | None = None,
        expert_reviewed: bool = False,
        allow_large_jump: bool = False,
    ) -> CropStageState:
        farm = await self.farms.get_for_user(farm_id, user.id)
        if farm is None:
            raise PermissionError("FARM_NOT_OWNED")
        if event == "evaluate":
            schedule = self.stage_registry.resolve(farm.crop)
            if schedule is None:
                evidence = StageEvidence(
                    registry_verified=False,
                    planting_date_present=farm.sowing_date is not None,
                    weather_source=evidence.weather_source,
                    image_observation=evidence.image_observation,
                    supports=list(evidence.supports),
                    conflicts=list(evidence.conflicts),
                    missing=["NO_VERIFIED_STAGE_MODEL"],
                )
            else:
                suggested_stage = None
                missing = list(evidence.missing)
                if farm.sowing_date is None:
                    missing.append("PLANTING_DATE_MISSING")
                else:
                    age_days = (datetime.now(UTC).date() - farm.sowing_date).days
                    if age_days < 0:
                        missing.append("PLANTING_DATE_IN_FUTURE")
                    else:
                        matched = next(
                            (
                                item
                                for item in schedule.stages
                                if item.start_offset <= age_days <= item.end_offset
                            ),
                            None,
                        )
                        suggested_stage = matched.code if matched else None
                        if matched is None:
                            missing.append("STAGE_WINDOW_UNAVAILABLE")
                evidence = StageEvidence(
                    registry_verified=True,
                    registry_version=schedule.version,
                    planting_date_present=farm.sowing_date is not None,
                    weather_source=evidence.weather_source,
                    image_observation=evidence.image_observation,
                    suggested_stage=suggested_stage,
                    supports=list(evidence.supports),
                    conflicts=list(evidence.conflicts),
                    missing=missing,
                )
        existing_event = (
            await self.session.execute(
                select(CropStageTransition).where(
                    CropStageTransition.user_id == user.id,
                    CropStageTransition.idempotency_key == idempotency_key,
                )
            )
        ).scalar_one_or_none()
        if existing_event:
            return await self.session.get(CropStageState, existing_event.state_id)
        row = await self.current(user, farm_id, crop_cycle_id)
        if row is not None and expected_version != row.version:
            raise StageConflictError("STALE_STAGE_VERSION")
        prior_state = StageState(row.state) if row else None
        prior_stage = row.confirmed_stage if row else None
        result = transition_stage(
            prior_state,
            event=event,
            evidence=evidence,
            stage=stage,
            prior_stage=prior_stage,
            allow_large_jump=allow_large_jump,
        )
        snapshot = {
            "registry_verified": evidence.registry_verified,
            "registry_version": evidence.registry_version,
            "planting_date_present": evidence.planting_date_present,
            "weather_source": evidence.weather_source,
            "image_observation": evidence.image_observation,
            "supports": evidence.supports,
            "conflicts": evidence.conflicts,
            "missing": evidence.missing,
            "recorded_at": datetime.now(UTC).isoformat(),
        }
        if row is None:
            row = CropStageState(
                user_id=user.id,
                farm_id=farm_id,
                crop_cycle_id=crop_cycle_id,
                state=result.state.value,
                suggested_stage=result.suggested_stage,
                confirmed_stage=result.confirmed_stage,
                registry_version=evidence.registry_version,
                calculation_version=CALCULATION_VERSION,
                version=1,
                pending_sync=False,
                evidence_snapshot=snapshot,
            )
            self.session.add(row)
            await self.session.flush()
        else:
            row.state = result.state.value
            row.suggested_stage = result.suggested_stage
            row.confirmed_stage = result.confirmed_stage or row.confirmed_stage
            row.registry_version = evidence.registry_version
            row.evidence_snapshot = snapshot
            row.version += 1
        self.session.add(
            CropStageTransition(
                state_id=row.id,
                user_id=user.id,
                event=event,
                prior_state=prior_state.value if prior_state else None,
                next_state=result.state.value,
                prior_stage=prior_stage,
                stage=result.confirmed_stage or result.suggested_stage,
                reason=reason,
                photo_reference=photo_reference,
                idempotency_key=idempotency_key,
                registry_version=evidence.registry_version,
                evidence_snapshot=snapshot,
                expert_reviewed=expert_reviewed,
            )
        )
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def history(self, user: User, state_id: uuid.UUID) -> list[CropStageTransition]:
        state = await self.session.get(CropStageState, state_id)
        if state is None or state.user_id != user.id:
            raise PermissionError("STAGE_STATE_NOT_OWNED")
        result = await self.session.execute(
            select(CropStageTransition)
            .where(CropStageTransition.state_id == state_id)
            .order_by(CropStageTransition.created_at)
        )
        return list(result.scalars())
