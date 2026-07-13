"""Disease report ORM model (docs/DATABASE_SCHEMA.md → Disease domain).

One consolidated, user- and farm-scoped report per diagnosis. Timeline-ready
(indexed by user/farm/crop/created_at) so future progression tracking, repeat
detection and weekly monitoring need no schema redesign (docs: STEP 7).
"""
from __future__ import annotations

import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.disease.constants import DEFAULT_LANGUAGE
from app.shared.base_model import (
    GUID,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)


class DiseaseReport(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "disease_reports"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True
    )
    # Reserved for crop-session linkage / progression tracking (docs: STEP 7).
    crop_session_id: Mapped[uuid.UUID | None] = mapped_column(GUID())

    image_url: Mapped[str] = mapped_column(String(512), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(512))
    capture_method: Mapped[str] = mapped_column(String(20), default="gallery")

    crop: Mapped[str | None] = mapped_column(String(80), index=True)
    crop_confidence: Mapped[int | None] = mapped_column(Integer)
    disease: Mapped[str | None] = mapped_column(String(200))
    confidence: Mapped[int | None] = mapped_column(Integer)
    severity: Mapped[str | None] = mapped_column(String(20))

    symptoms: Mapped[list | None] = mapped_column(JSON)
    causes: Mapped[list | None] = mapped_column(JSON)
    recommendations: Mapped[list | None] = mapped_column(JSON)
    prevention: Mapped[list | None] = mapped_column(JSON)
    visible_parts: Mapped[list | None] = mapped_column(JSON)
    needs_expert_review: Mapped[bool] = mapped_column(Boolean, default=False)

    explanation_tamil: Mapped[str | None] = mapped_column(Text)
    explanation_english: Mapped[str | None] = mapped_column(Text)

    model_used: Mapped[str | None] = mapped_column(String(60))
    raw_response: Mapped[dict | None] = mapped_column(JSON)
    weather_snapshot: Mapped[dict | None] = mapped_column(JSON)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    language: Mapped[str] = mapped_column(
        String(5), default=DEFAULT_LANGUAGE, nullable=False
    )
