from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.action_verification.models import ActionWorkflow
from app.modules.auth.models import User
from app.modules.daily_task.models import DailyTask
from app.modules.farms.exceptions import FarmNotFoundError
from app.modules.farms.repositories import FarmRepository
from app.modules.organic.certification_receipt import LOGBOOK_EVIDENCE, upload_receipt_is_valid
from app.modules.organic.models import OrganicUploadAttestation

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
                action is None
                or action.is_deleted
                or action.user_id != user.id
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
        source_feature = (
            action.source_module if action else ("daily_task" if task else "farmer_logbook")
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
            expense_amount_inr=payload.expense_amount_inr,
            voice_transcript=payload.voice_transcript,
            outcome_status=payload.outcome_status,
            source_feature=source_feature,
            source_record_id=source_record_id,
            source_version=source_version,
            source_verified=bool(action and action.source_verified),
            verification_status="farmer_reported",
            expert_reviewed=False,
            idempotency_key=payload.idempotency_key,
        )
        evidence_rows = []
        for item in payload.evidence:
            attestation = await self.session.get(
                OrganicUploadAttestation, item.upload_attestation_id
            )
            if attestation is None or not upload_receipt_is_valid(
                attestation=attestation,
                user_id=user.id,
                farm_id=payload.farm_id,
                purpose=LOGBOOK_EVIDENCE,
                receipt=item.upload_receipt,
            ):
                raise OrganicLogReferenceError()
            attestation.consumed_at = datetime.now(UTC)
            evidence_rows.append(
                OrganicPracticeEvidence(
                    upload_attestation_id=attestation.id,
                    evidence_type=item.evidence_type,
                    storage_ref=attestation.object_key,
                    content_hash=attestation.sha256,
                    mime_type=attestation.mime_type,
                    captured_at=item.captured_at,
                    retention_consent=item.retention_consent,
                    farmer_reported=True,
                    expert_reviewed=False,
                )
            )
        row.evidence = evidence_rows
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row, attribute_names=["evidence"])
        return row

    async def record_completed_action(
        self, user: User, action: ActionWorkflow
    ) -> OrganicPracticeLogEntry | None:
        """Bridge a farmer-reported workflow completion into the unified log.

        This records workflow completion only. It does not assert efficacy,
        expert review, certification, or that a satellite observation diagnosed
        the cause of a field condition.
        """
        supported_source = action.source_module.startswith("organic_") or action.source_module in {
            "satellite_field_scouting", "satellite_scouting_followup"
        }
        if not supported_source or action.status != "farmer_reported_done":
            return None
        key = f"completed-action:{action.id}"
        existing = (
            await self.session.execute(
                select(OrganicPracticeLogEntry).where(
                    OrganicPracticeLogEntry.user_id == user.id,
                    OrganicPracticeLogEntry.idempotency_key == key,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing
        practice_type = {
            "organic_soil_plan": "amendment",
            "organic_disease_plan": (
                "biological_treatment" if action.action_code.startswith("organic_input.")
                else "scouting" if action.action_code in {
                    "organic.disease.confirm_symptoms", "organic.disease.reinspect"
                } else "custom"
            ),
            "organic_calendar": "custom",
            "organic_weather_gate": "custom",
            "satellite_field_scouting": "scouting",
            "satellite_scouting_followup": "custom",
        }.get(action.source_module, "custom")
        row = OrganicPracticeLogEntry(
            user_id=user.id,
            farm_id=action.farm_id,
            crop_cycle_id=action.crop_cycle_id,
            action_workflow_id=action.id,
            practice_type=practice_type,
            practice_code=action.action_code,
            occurred_at=datetime.now(UTC),
            outcome_status="not_reported",
            source_feature=action.source_module,
            source_record_id=action.source_record_id,
            source_version=action.source_version,
            source_verified=action.source_verified,
            verification_status="farmer_reported",
            expert_reviewed=False,
            idempotency_key=key,
        )
        try:
            async with self.session.begin_nested():
                self.session.add(row)
                await self.session.flush()
        except IntegrityError:
            existing = (
                await self.session.execute(
                    select(OrganicPracticeLogEntry).where(
                        OrganicPracticeLogEntry.user_id == user.id,
                        OrganicPracticeLogEntry.idempotency_key == key,
                    )
                )
            ).scalar_one_or_none()
            if existing is not None:
                return existing
            raise
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
