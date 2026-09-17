from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import GUID, Base, TimestampMixin, UUIDMixin


class DiseaseRiskAlert(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "disease_risk_alerts"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_disease_risk_user_key"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), index=True)
    farm_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("farms.id"), index=True)
    crop: Mapped[str] = mapped_column(String(80), nullable=False)
    disease_key: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    risk_level: Mapped[str | None] = mapped_column(String(20))
    # Qualitative evidence labels are intentionally descriptive; the longest
    # released value (``sourced_public_reference_evidence``) exceeds 30 chars.
    confidence: Mapped[str] = mapped_column(String(50), nullable=False)
    weather_factors: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    weather_source: Mapped[str] = mapped_column(String(20), nullable=False)
    weather_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    crop_stage: Mapped[str | None] = mapped_column(String(30))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rule_pack_id: Mapped[str | None] = mapped_column(String(100))
    rule_version: Mapped[str | None] = mapped_column(String(40))
    rule_verification_status: Mapped[str] = mapped_column(String(30), nullable=False)
    farmer_message_key: Mapped[str] = mapped_column(String(100), nullable=False)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    missing_inputs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    notification_emitted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
