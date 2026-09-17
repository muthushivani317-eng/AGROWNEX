"""Pilot data is distinct from certification evidence and existing farm records."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import Base, GUID, TimestampMixin, UUIDMixin


class OrganicFpo(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organic_fpos"
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    district: Mapped[str] = mapped_column(String(80), nullable=False)
    registration_reference: Mapped[str | None] = mapped_column(String(120))
    is_test: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class OrganicPartnerOrganization(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organic_partner_organizations"
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    fpo_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("organic_fpos.id"), unique=True)
    is_test: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class OrganicPartnerStaff(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organic_partner_staff"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_organic_partner_staff"),)
    organization_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("organic_partner_organizations.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")


class OrganicPartnerApiKey(UUIDMixin, TimestampMixin, Base):
    """A partner organization's credential for the read-only external feed
    (see organic_mvp.partner_feed_router). One key belongs to exactly one
    organization -- the feed's auth dependency resolves organization_id from
    this row only, never from anything client-supplied, which is what keeps
    one FPO from ever being able to read another FPO's data.
    """

    __tablename__ = "organic_partner_api_keys"
    organization_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("organic_partner_organizations.id"), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    # Short, non-secret lookup key (indexed, unique). The secret itself is
    # never stored -- only its peppered HMAC-SHA256 hash (see
    # app.modules.auth.security.hash_token), mirroring how refresh tokens
    # are handled.
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False, unique=True, index=True)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OrganicPartnerFarmerLink(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organic_partner_farmer_links"
    __table_args__ = (UniqueConstraint("organization_id", "farmer_user_id", name="uq_organic_partner_farmer"),)
    organization_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("organic_partner_organizations.id"), nullable=False, index=True)
    farmer_user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OrganicPilot(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organic_pilots"
    fpo_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("organic_fpos.id"))
    fpo_name: Mapped[str | None] = mapped_column(String(180))
    district: Mapped[str | None] = mapped_column(String(80))
    crop_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    agronomist_user_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    certification_pathway: Mapped[str | None] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="setup_required")
    is_test: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class OrganicPilotEnrollment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organic_pilot_enrollments"
    __table_args__ = (UniqueConstraint("pilot_id", "farm_id", name="uq_organic_pilot_farm"),)
    pilot_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("organic_pilots.id"), nullable=False, index=True)
    farm_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("farms.id"), nullable=False, index=True)
    farmer_user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="enrolled")
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OrganicPlot(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organic_plots"
    farm_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("farms.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    area_hectares: Mapped[float | None] = mapped_column(Float)
    boundary_geojson: Mapped[dict | None] = mapped_column(JSON)
    trial_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class OrganicCropCycle(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organic_crop_cycles"
    plot_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("organic_plots.id"), nullable=False, index=True)
    crop_id: Mapped[str] = mapped_column(String(80), nullable=False)
    sowing_date: Mapped[date | None] = mapped_column(Date)
    expected_harvest_start: Mapped[date | None] = mapped_column(Date)
    expected_harvest_end: Mapped[date | None] = mapped_column(Date)
    expected_quantity_kg: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(24), nullable=False, default="farmer_entered")


class OrganicReadiness(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organic_readiness_assessments"
    farm_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("farms.id"), nullable=False, index=True)
    farmer_user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    answers: Mapped[dict] = mapped_column(JSON, nullable=False)
    rules_version: Mapped[str | None] = mapped_column(String(60))
    score: Mapped[int | None] = mapped_column(Integer)
    pathway: Mapped[str] = mapped_column(String(40), nullable=False, default="awaiting_review")
    risk_flags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class OrganicReadinessRules(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organic_readiness_rules"
    version: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    questions: Mapped[list] = mapped_column(JSON, nullable=False)
    scoring: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    approved_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OrganicTaskTemplate(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organic_task_templates"
    __table_args__ = (UniqueConstraint("crop_id", "district", "version", name="uq_organic_template_version"),)
    crop_id: Mapped[str] = mapped_column(String(80), nullable=False)
    district: Mapped[str] = mapped_column(String(80), nullable=False)
    version: Mapped[str] = mapped_column(String(60), nullable=False)
    tasks: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    agronomist_user_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[str | None] = mapped_column(Text)


class OrganicScheduledTask(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organic_scheduled_tasks"
    crop_cycle_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("organic_crop_cycles.id"), nullable=False, index=True)
    template_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("organic_task_templates.id"), nullable=False)
    day_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    due_on: Mapped[date] = mapped_column(Date, nullable=False)
    title_ta: Mapped[str] = mapped_column(String(240), nullable=False)
    body_ta: Mapped[str] = mapped_column(Text, nullable=False)
    title_en: Mapped[str | None] = mapped_column(String(240))
    body_en: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")


class OrganicPgsCase(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organic_pgs_cases"
    farm_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("farms.id"), nullable=False, unique=True)
    farmer_user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="pre_certification_trial")
    partial_conversion: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    checklist: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    regional_council_approval_ref: Mapped[str | None] = mapped_column(String(180))
    certificate_id: Mapped[str | None] = mapped_column(String(160))
    certificate_document_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("organic_certification_documents.id"))
    issuing_authority: Mapped[str | None] = mapped_column(String(180))
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    non_compliance_note: Mapped[str | None] = mapped_column(Text)


class OrganicPeerAppraisal(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organic_peer_appraisals"
    case_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("organic_pgs_cases.id"), nullable=False, index=True)
    scheduled_on: Mapped[date] = mapped_column(Date, nullable=False)
    peer_user_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="scheduled")
    findings: Mapped[dict | None] = mapped_column(JSON)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
