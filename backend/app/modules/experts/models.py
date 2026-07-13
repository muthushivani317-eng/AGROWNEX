"""Expert Connect ORM models (docs: future-ready consultation platform).

Normalized tables:

* ``experts``                     — a verified agricultural expert *desk* (TNAU /
  KVK / Government / Kisan Call Centre / private). Institutional, never fabricated
  individuals. ``rating`` is nullable and never invented.
* ``expert_specializations``      — the categories/crops a desk covers (drives
  deterministic assignment).
* ``expert_availability``         — weekly availability windows (future-ready for
  scheduling / live chat / video).
* ``consultations``               — one farmer question thread. Farmer-scoped;
  optional farm/crop; assigned to a desk by the engine.
* ``consultation_messages``       — the immutable conversation timeline (farmer /
  expert / system). Never edited.
* ``consultation_attachments``    — photos now (voice/video reserved) stored in
  R2/S3; DB keeps only the URL + metadata.
* ``consultation_status_history`` — every status change is logged.

``farmer_id`` is the authenticated user (FK ``users.id``), matching every module.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.experts.constants import (
    AttachmentKind,
    ConsultationChannel,
    ConsultationPriority,
    ConsultationStatus,
    ExpertType,
    SenderType,
)
from app.shared.base_model import (
    GUID,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)


class Expert(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "experts"

    # Optional link to a platform user (an expert may log in later); nullable so
    # institutional desks exist without a user account.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True
    )
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    expert_type: Mapped[str] = mapped_column(
        String(24), default=ExpertType.TNAU.value, nullable=False, index=True
    )
    organization: Mapped[str | None] = mapped_column(String(160))
    title: Mapped[str | None] = mapped_column(String(120))
    bio: Mapped[str | None] = mapped_column(Text)
    photo_url: Mapped[str | None] = mapped_column(String(512))

    # Coverage — served districts + spoken languages (JSON lists, PostGIS not needed).
    districts: Mapped[list | None] = mapped_column(JSON)
    languages: Mapped[list | None] = mapped_column(JSON)

    years_experience: Mapped[int | None] = mapped_column(Integer)
    # Rating is never fabricated — null until real feedback exists.
    rating: Mapped[float | None] = mapped_column(Float)
    rating_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(12), default="active", nullable=False, index=True
    )
    slug: Mapped[str | None] = mapped_column(String(120), index=True)
    source: Mapped[str | None] = mapped_column(String(120))
    contact: Mapped[str | None] = mapped_column(String(160))

    specializations: Mapped[list[ExpertSpecialization]] = relationship(
        back_populates="expert",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    availability: Mapped[list[ExpertAvailability]] = relationship(
        back_populates="expert",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class ExpertSpecialization(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "expert_specializations"

    expert_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("experts.id"), index=True, nullable=False
    )
    category: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    crop: Mapped[str | None] = mapped_column(String(80), index=True)

    expert: Mapped[Expert] = relationship(back_populates="specializations")


class ExpertAvailability(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "expert_availability"

    expert_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("experts.id"), index=True, nullable=False
    )
    # 0=Mon … 6=Sun; null = generally available (future-ready for scheduling).
    day_of_week: Mapped[int | None] = mapped_column(Integer)
    start_time: Mapped[str | None] = mapped_column(String(5))  # "HH:MM"
    end_time: Mapped[str | None] = mapped_column(String(5))
    timezone: Mapped[str] = mapped_column(
        String(40), default="Asia/Kolkata", nullable=False
    )
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    expert: Mapped[Expert] = relationship(back_populates="availability")


class Consultation(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "consultations"

    farmer_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True
    )
    assigned_expert_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("experts.id"), index=True
    )
    # Reserved link to a crop/growth session (future timeline joins); nullable.
    crop_session_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), index=True)

    category: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    crop: Mapped[str | None] = mapped_column(String(80), index=True)
    subject: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(
        String(12), default=ConsultationPriority.MEDIUM.value, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default=ConsultationStatus.SUBMITTED.value,
        nullable=False, index=True,
    )
    channel: Mapped[str] = mapped_column(
        String(12), default=ConsultationChannel.IN_APP.value, nullable=False
    )
    language: Mapped[str] = mapped_column(String(8), default="ta", nullable=False)

    resolution_note: Mapped[str | None] = mapped_column(Text)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    expert: Mapped[Expert | None] = relationship(lazy="selectin")
    messages: Mapped[list[ConsultationMessage]] = relationship(
        back_populates="consultation",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="ConsultationMessage.created_at",
    )
    attachments: Mapped[list[ConsultationAttachment]] = relationship(
        back_populates="consultation",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="ConsultationAttachment.created_at",
    )
    status_history: Mapped[list[ConsultationStatusHistory]] = relationship(
        back_populates="consultation",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="ConsultationStatusHistory.created_at",
    )


class ConsultationMessage(UUIDMixin, TimestampMixin, Base):
    """Immutable conversation entry (docs: conversation immutable)."""

    __tablename__ = "consultation_messages"

    consultation_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("consultations.id"), index=True, nullable=False
    )
    sender_type: Mapped[str] = mapped_column(
        String(8), default=SenderType.FARMER.value, nullable=False
    )
    sender_user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id")
    )
    sender_expert_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("experts.id")
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(8), default="ta", nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    consultation: Mapped[Consultation] = relationship(back_populates="messages")


class ConsultationAttachment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "consultation_attachments"

    consultation_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("consultations.id"), index=True, nullable=False
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("consultation_messages.id"), index=True
    )
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id")
    )
    kind: Mapped[str] = mapped_column(
        String(12), default=AttachmentKind.IMAGE.value, nullable=False
    )
    file_url: Mapped[str] = mapped_column(String(512), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(512))
    mime_type: Mapped[str | None] = mapped_column(String(80))
    file_size: Mapped[int | None] = mapped_column(Integer)
    caption: Mapped[str | None] = mapped_column(String(255))

    consultation: Mapped[Consultation] = relationship(back_populates="attachments")


class ConsultationStatusHistory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "consultation_status_history"

    consultation_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("consultations.id"), index=True, nullable=False
    )
    old_status: Mapped[str | None] = mapped_column(String(20))
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_by_type: Mapped[str] = mapped_column(
        String(8), default=SenderType.SYSTEM.value, nullable=False
    )
    changed_by_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    note: Mapped[str | None] = mapped_column(String(255))

    consultation: Mapped[Consultation] = relationship(back_populates="status_history")
