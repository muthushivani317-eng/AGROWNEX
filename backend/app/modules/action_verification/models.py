from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import GUID, Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class ActionWorkflow(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "action_workflows"

    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), index=True)
    farm_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("farms.id"), index=True)
    crop_cycle_id: Mapped[str | None] = mapped_column(String(80))
    source_module: Mapped[str] = mapped_column(String(40), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(100), nullable=False)
    source_version: Mapped[str] = mapped_column(String(80), nullable=False)
    action_code: Mapped[str] = mapped_column(String(120), nullable=False)
    source_verified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    farmer_created: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    suggestion_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    outcome_status: Mapped[str] = mapped_column(String(40), default="not_reported")
    verification_scope: Mapped[str] = mapped_column(
        String(40), default="workflow_completion_only", nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    pending_sync: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "user_id", "farm_id", "source_module", "source_record_id",
            name="uq_action_source_identity",
        ),
    )


class ActionAuditEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "action_audit_events"

    action_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("action_workflows.id"), index=True
    )
    actor_user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"))
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    event: Mapped[str] = mapped_column(String(30), nullable=False)
    prior_status: Mapped[str | None] = mapped_column(String(40))
    new_status: Mapped[str] = mapped_column(String(40), nullable=False)
    request_id: Mapped[str] = mapped_column(String(100), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    source_version: Mapped[str] = mapped_column(String(80), nullable=False)
    note: Mapped[str | None] = mapped_column(String(500))
    reason: Mapped[str | None] = mapped_column(String(500))
    evidence_hash: Mapped[str | None] = mapped_column(String(64))
    evidence_storage_ref: Mapped[str | None] = mapped_column(String(512))
    evidence_mime_type: Mapped[str | None] = mapped_column(String(40))
    evidence_captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retention_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    supersedes_event_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    farmer_reported: Mapped[bool] = mapped_column(Boolean, default=False)
    expert_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    event_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
