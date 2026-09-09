from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import GUID, Base, TimestampMixin, UUIDMixin


class OrganicFarmProfile(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organic_farm_profiles"

    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="conventional")
    transition_start_date: Mapped[date | None] = mapped_column(Date)
    goals: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    preferred_practices: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    avoided_input_categories: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    certification_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="not_claimed", index=True
    )
    certification_scheme: Mapped[str | None] = mapped_column(String(120))
    certification_identifier: Mapped[str | None] = mapped_column(String(160))
    certificate_issued_on: Mapped[date | None] = mapped_column(Date)
    certificate_expires_on: Mapped[date | None] = mapped_column(Date)
    certification_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    certification_verified_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL")
    )
    plan_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_idempotency_key: Mapped[str | None] = mapped_column(String(128))

    documents: Mapped[list[OrganicCertificationDocument]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", lazy="selectin"
    )


class OrganicCertificationDocument(UUIDMixin, TimestampMixin, Base):
    """Private object metadata. Object URLs are never exposed by public profile/library APIs."""

    __tablename__ = "organic_certification_documents"
    __table_args__ = (
        UniqueConstraint(
            "profile_id", "idempotency_key", name="uq_organic_cert_document_idempotency"
        ),
    )

    profile_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("organic_farm_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    review_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="document_submitted"
    )

    profile: Mapped[OrganicFarmProfile] = relationship(back_populates="documents")


class OrganicInput(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organic_inputs"
    __table_args__ = (
        UniqueConstraint("slug", "source_version", name="uq_organic_input_slug_version"),
    )

    slug: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    name_en: Mapped[str] = mapped_column(String(180), nullable=False)
    name_ta: Mapped[str] = mapped_column(String(180), nullable=False)
    purpose_en: Mapped[str] = mapped_column(Text, nullable=False)
    purpose_ta: Mapped[str] = mapped_column(Text, nullable=False)
    guidance: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    applicable_crops: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    applicable_stages: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    applicable_regions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    limitations: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    source_organization: Mapped[str] = mapped_column(String(180), nullable=False)
    document_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(String(512), nullable=False)
    source_version: Mapped[str] = mapped_column(String(80), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    review_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="draft", index=True
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_from: Mapped[date | None] = mapped_column(Date)
    review_due_on: Mapped[date | None] = mapped_column(Date)
