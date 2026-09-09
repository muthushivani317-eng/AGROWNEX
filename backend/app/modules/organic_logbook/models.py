from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import GUID, Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class OrganicPracticeLogEntry(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Farmer-owned record of a performed organic practice.

    ``verification_status`` deliberately describes only who reported/reviewed
    the record. It must never be interpreted as proof of agronomic efficacy or
    organic certification.
    """

    __tablename__ = "organic_practice_log_entries"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=False, index=True
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), nullable=False, index=True
    )
    crop_cycle_id: Mapped[str | None] = mapped_column(String(80))
    action_workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("action_workflows.id"), index=True
    )
    daily_task_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("daily_tasks.id"), index=True
    )
    practice_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    practice_code: Mapped[str] = mapped_column(String(120), nullable=False)
    input_reference: Mapped[str | None] = mapped_column(String(120))
    quantity: Mapped[float | None] = mapped_column(Float)
    quantity_unit: Mapped[str | None] = mapped_column(String(30))
    treated_area_hectares: Mapped[float | None] = mapped_column(Float)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    outcome_status: Mapped[str] = mapped_column(String(40), nullable=False, default="not_reported")
    source_feature: Mapped[str] = mapped_column(String(40), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(100), nullable=False)
    source_version: Mapped[str] = mapped_column(String(80), nullable=False)
    source_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification_status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="farmer_reported"
    )
    expert_reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)

    evidence: Mapped[list[OrganicPracticeEvidence]] = relationship(
        back_populates="entry", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_organic_log_user_idempotency"),
        Index("ix_organic_log_farm_occurred", "farm_id", "occurred_at"),
    )


class OrganicPracticeEvidence(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organic_practice_evidence"

    entry_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organic_practice_log_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    upload_attestation_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("organic_upload_attestations.id"), unique=True
    )
    evidence_type: Mapped[str] = mapped_column(String(20), nullable=False)
    storage_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    mime_type: Mapped[str | None] = mapped_column(String(80))
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retention_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    farmer_reported: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    expert_reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    entry: Mapped[OrganicPracticeLogEntry] = relationship(back_populates="evidence")
