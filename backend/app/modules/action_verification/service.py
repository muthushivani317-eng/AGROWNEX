from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.farms.exceptions import FarmNotFoundError
from app.modules.farms.repositories import FarmRepository

from .engine import ActionStatus, transition
from .evidence import validate_evidence
from .exceptions import ActionNotFoundError
from .models import ActionAuditEvent, ActionWorkflow
from .schemas import ActionCreateIn, ActionRespondIn
from .source_adapter import SourceAction


class ActionVerificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.farms = FarmRepository(session)

    async def _farm(self, user: User, farm_id: uuid.UUID):
        farm = await self.farms.get_for_user(farm_id, user.id)
        if farm is None:
            # NotFoundError (404), not PermissionError -- matches the app's
            # "404-not-403" ownership convention (see .exceptions) and is
            # actually handled by the global AppError handler instead of
            # falling through to a raw 500.
            raise FarmNotFoundError()
        return farm

    async def _action(self, user: User, action_id: uuid.UUID) -> ActionWorkflow:
        row = await self.session.get(ActionWorkflow, action_id)
        if row is None or row.user_id != user.id or row.is_deleted:
            raise ActionNotFoundError()
        await self._farm(user, row.farm_id)
        return row

    async def _action_for_update(self, user: User, action_id: uuid.UUID) -> ActionWorkflow:
        row = (
            await self.session.execute(
                select(ActionWorkflow)
                .where(
                    ActionWorkflow.id == action_id,
                    ActionWorkflow.user_id == user.id,
                    ActionWorkflow.is_deleted.is_(False),
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if row is None:
            raise ActionNotFoundError()
        await self._farm(user, row.farm_id)
        return row

    async def create(self, user: User, payload: ActionCreateIn) -> ActionWorkflow:
        await self._farm(user, payload.farm_id)
        existing = (
            await self.session.execute(
                select(ActionWorkflow).where(
                    ActionWorkflow.user_id == user.id,
                    ActionWorkflow.source_module == payload.source_feature,
                    ActionWorkflow.source_record_id == payload.source_record_id,
                    ActionWorkflow.action_code == payload.action_code,
                    ActionWorkflow.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        if existing:
            return existing
        row = ActionWorkflow(
            user_id=user.id,
            farm_id=payload.farm_id,
            crop_cycle_id=payload.crop_cycle_id,
            source_module=payload.source_feature,
            source_record_id=payload.source_record_id,
            source_version=payload.source_version,
            action_code=payload.action_code,
            source_verified=False,
            farmer_created=True,
            suggestion_time=payload.suggestion_time,
            due_at=payload.due_at,
            expires_at=payload.expires_at,
            status=ActionStatus.SUGGESTED.value,
            outcome_status="not_reported",
            verification_scope="workflow_completion_only",
            version=1,
            pending_sync=False,
        )
        self.session.add(row)
        await self.session.flush()
        self.session.add(self._event(row, user, "suggest", None, "created", "created"))
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def register_source_action(
        self,
        user: User,
        farm_id: uuid.UUID,
        source: SourceAction,
    ) -> ActionWorkflow | None:
        """Idempotently reference an action produced by a trusted server module."""
        await self._farm(user, farm_id)
        now = datetime.now(UTC)
        if not source.actionable or (source.expires_at and source.expires_at <= now):
            return None
        existing = (
            await self.session.execute(
                select(ActionWorkflow).where(
                    ActionWorkflow.user_id == user.id,
                    ActionWorkflow.farm_id == farm_id,
                    ActionWorkflow.source_module == source.source_feature,
                    ActionWorkflow.source_record_id == source.source_record_id,
                    ActionWorkflow.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()
        if existing:
            return existing
        row = ActionWorkflow(
            user_id=user.id,
            farm_id=farm_id,
            crop_cycle_id=source.crop_cycle_id,
            source_module=source.source_feature,
            source_record_id=source.source_record_id,
            source_version=source.source_version,
            action_code=source.action_code,
            source_verified=source.source_verified,
            farmer_created=False,
            suggestion_time=source.suggestion_time,
            due_at=source.due_at,
            expires_at=source.expires_at,
            status=ActionStatus.SUGGESTED.value,
            outcome_status="not_reported",
            verification_scope="workflow_completion_only",
            version=1,
            pending_sync=False,
        )
        try:
            # The SELECT above is only a fast path, not the real guarantee --
            # two concurrent requests (e.g. the home-screen weather widget and
            # a /notifications sync, both landing on the same farm within the
            # same day) can both see "no existing row" and both reach this
            # insert. Scope the insert to its own SAVEPOINT so a lost race
            # only unwinds this nested block, not the whole request's
            # transaction: without this, the IntegrityError from the unique
            # constraint (uq_action_source_identity) left the outer session's
            # transaction in a "pending rollback" state, and the very next
            # query on that same session -- often unrelated, e.g. notification
            # preference checks -- raised PendingRollbackError and turned a
            # harmless duplicate into a real 500 for the caller (observed in
            # production logs, 2026-09-08: GET /notifications 500 caused by a
            # weather-sourced action losing exactly this race).
            async with self.session.begin_nested():
                self.session.add(row)
                await self.session.flush()
        except IntegrityError:
            existing = (
                await self.session.execute(
                    select(ActionWorkflow).where(
                        ActionWorkflow.user_id == user.id,
                        ActionWorkflow.farm_id == farm_id,
                        ActionWorkflow.source_module == source.source_feature,
                        ActionWorkflow.source_record_id == source.source_record_id,
                        ActionWorkflow.is_deleted.is_(False),
                    )
                )
            ).scalar_one_or_none()
            if existing is not None:
                return existing
            raise
        self.session.add(
            self._event(row, user, "suggest", None, "source-created", source.source_record_id)
        )
        await self.session.flush()
        await self.session.refresh(row)
        return row

    def _event(self, row, user, event, prior, request_id, key, **extra):
        return ActionAuditEvent(
            action_id=row.id,
            actor_user_id=user.id,
            actor_type="farmer",
            event=event,
            prior_status=prior,
            new_status=row.status,
            request_id=request_id,
            idempotency_key=key,
            source_version=row.source_version,
            farmer_reported=event not in {"suggest", "view"},
            expert_reviewed=False,
            retention_consent=extra.get("retention_consent", False),
            note=extra.get("note"),
            reason=extra.get("reason"),
            evidence_hash=extra.get("evidence_hash"),
            evidence_mime_type=extra.get("evidence_mime_type"),
            event_snapshot={
                "verification_scope": "workflow_completion_only",
                "source_feature": row.source_module,
                "source_record_id": row.source_record_id,
                "status": row.status,
            },
        )

    async def list(self, user: User, *, pending_only: bool = False):
        query = select(ActionWorkflow).where(
            ActionWorkflow.user_id == user.id, ActionWorkflow.is_deleted.is_(False)
        )
        if pending_only:
            query = query.where(
                ActionWorkflow.status.in_(["suggested", "viewed", "deferred"]),
                or_(
                    ActionWorkflow.expires_at.is_(None),
                    ActionWorkflow.expires_at > datetime.now(UTC),
                ),
            )
        result = await self.session.execute(query.order_by(ActionWorkflow.created_at.desc()))
        return list(result.scalars())

    async def get(self, user: User, action_id: uuid.UUID):
        return await self._action(user, action_id)

    async def respond(self, user: User, action_id: uuid.UUID, payload: ActionRespondIn):
        # Serialize competing transitions for the same action. The version check
        # below then remains meaningful under concurrent requests on databases
        # that support row-level locks (PostgreSQL in production).
        row = await self._action_for_update(user, action_id)
        duplicate = (
            await self.session.execute(
                select(ActionAuditEvent).where(
                    ActionAuditEvent.actor_user_id == user.id,
                    ActionAuditEvent.idempotency_key == payload.idempotency_key,
                )
            )
        ).scalar_one_or_none()
        if duplicate:
            return row
        if row.expires_at and row.expires_at < datetime.now(UTC):
            raise ValueError("ACTION_EXPIRED")
        if row.version != payload.expected_version:
            raise ValueError("ACTION_VERSION_CONFLICT")
        evidence_hash = None
        if payload.evidence_base64 and payload.evidence_mime_type:
            evidence_hash = validate_evidence(
                payload.evidence_base64,
                payload.evidence_mime_type,
                consent=payload.retention_consent,
            ).sha256
        prior = row.status
        row.status = transition(ActionStatus(row.status), payload.event).value
        row.version += 1
        self.session.add(
            self._event(
                row,
                user,
                payload.event,
                prior,
                payload.request_id,
                payload.idempotency_key,
                note=payload.note,
                reason=payload.reason,
                evidence_hash=evidence_hash,
                evidence_mime_type=payload.evidence_mime_type,
                retention_consent=payload.retention_consent,
            )
        )
        await self.session.flush()
        await self.session.refresh(row)
        if row.status == ActionStatus.FARMER_REPORTED_DONE.value:
            # The logbook is a downstream audit projection of this canonical
            # workflow, not an expert or efficacy verification.
            from app.modules.organic_logbook.service import OrganicLogbookService

            await OrganicLogbookService(self.session).record_completed_action(user, row)
        return row

    async def history(self, user: User, action_id: uuid.UUID):
        await self._action(user, action_id)
        result = await self.session.execute(
            select(ActionAuditEvent)
            .where(ActionAuditEvent.action_id == action_id)
            .order_by(ActionAuditEvent.created_at)
        )
        return list(result.scalars())
