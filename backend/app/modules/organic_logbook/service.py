from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.action_verification.models import ActionWorkflow
from app.modules.auth.models import User
from app.modules.daily_task.models import DailyTask
from app.modules.farms.exceptions import FarmNotFoundError
from app.modules.farms.repositories import FarmRepository

from .exceptions import OrganicLogEntryNotFoundError, OrganicLogReferenceError
from .models import OrganicPracticeEvidence, OrganicPracticeLogEntry
from .schemas import OrganicLogCreateIn


class OrganicLogbookService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.farms = FarmRepository(session)

    async def _owned_farm(self, user: User, farm_id: uuid.UUID) -> None:
        if await self.farms.get_for_user(farm_id, user.id) is None:
            raise FarmNotFoundError()

    async def _references(self, user: User, payload: OrganicLogCreateIn):
        action = None
        task = None
        if payload.action_workflow_id:
            action = await self.session.get(ActionWorkflow, payload.action_workflow_id)
            if (
                action is None or action.is_deleted or action.user_id != user.id
                or action.farm_id != payload.farm_id
            ):
                raise OrganicLogReferenceError()
        if payload.daily_task_id:
            task = await self.session.get(DailyTask, payload.daily_task_id)
            if task is None or task.user_id != user.id or task.farm_id != payload.farm_id:
                raise OrganicLogReferenceError()
        return action, task

    async def create(self, user: User, payload: OrganicLogCreateIn) -> OrganicPracticeLogEntry:
        await self._owned_farm(user, payload.farm_id)
        expected_prefix = f"organic-evidence/{user.id}/{payload.farm_id}/"
        if any(not item.storage_ref.startswith(expected_prefix) for item in payload.evidence):
            raise OrganicLogReferenceError()
        existing = (
            await self.session.execute(
                select(OrganicPracticeLogEntry).where(
                    OrganicPracticeLogEntry.user_id == user.id,
                    OrganicPracticeLogEntry.idempotency_key == payload.idempotency_key,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing
        action, task = await self._references(user, payload)
        if payload.occurred_at.astimezone(UTC) > datetime.now(UTC):
            raise ValueError("ORGANIC_LOG_EVENT_IN_FUTURE")

        # Provenance comes from the server-owned workflow when one is linked;
        # manual records remain explicitly farmer sourced and unverified.
        source_feature = action.source_module if action else (
            "daily_task" if task else "farmer_logbook"
        )
        source_record_id = (
            action.source_record_id if action else str(task.id) if task else payload.idempotency_key
        )
        source_version = action.source_version if action else "1"
        row = OrganicPracticeLogEntry(
            user_id=user.id,
            farm_id=payload.farm_id,
            crop_cycle_id=payload.crop_cycle_id or (action.crop_cycle_id if action else None),
            action_workflow_id=payload.action_workflow_id,
            daily_task_id=payload.daily_task_id,
            practice_type=payload.practice_type,
            practice_code=payload.practice_code,
            input_reference=payload.input_reference,
            quantity=payload.quantity,
            quantity_unit=payload.quantity_unit,
            treated_area_hectares=payload.treated_area_hectares,
            occurred_at=payload.occurred_at,
            note=payload.note,
            outcome_status=payload.outcome_status,
            source_feature=source_feature,
            source_record_id=source_record_id,
            source_version=source_version,
            source_verified=bool(action and action.source_verified),
            verification_status="farmer_reported",
            expert_reviewed=False,
            idempotency_key=payload.idempotency_key,
        )
        row.evidence = [
            OrganicPracticeEvidence(
                **item.model_dump(), farmer_reported=True, expert_reviewed=False
            )
            for item in payload.evidence
        ]
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row, attribute_names=["evidence"])
        return row

    async def list(self, user: User, *, farm_id: uuid.UUID | None = None):
        query = select(OrganicPracticeLogEntry).where(
            OrganicPracticeLogEntry.user_id == user.id,
            OrganicPracticeLogEntry.is_deleted.is_(False),
        )
        if farm_id is not None:
            await self._owned_farm(user, farm_id)
            query = query.where(OrganicPracticeLogEntry.farm_id == farm_id)
        result = await self.session.execute(
            query.order_by(OrganicPracticeLogEntry.occurred_at.desc())
        )
        return list(result.scalars().unique())

    async def get(self, user: User, entry_id: uuid.UUID):
        row = await self.session.get(OrganicPracticeLogEntry, entry_id)
        if row is None or row.user_id != user.id or row.is_deleted:
            raise OrganicLogEntryNotFoundError()
        await self._owned_farm(user, row.farm_id)
        return row
