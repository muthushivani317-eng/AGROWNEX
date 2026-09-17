"""Disease report ORM model (docs/DATABASE_SCHEMA.md → Disease domain).

One consolidated, user- and farm-scoped report per diagnosis. Timeline-ready
(indexed by user/farm/crop/created_at) so future progression tracking, repeat
detection and weekly monitoring need no schema redesign (docs: STEP 7).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from app.modules.disease.constants import DEFAULT_LANGUAGE
from app.shared.base_model import (
    GUID,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)
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

    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    image_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
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
    # Category-level-only conventional (non-organic) guidance -- e.g. "a
    # protectant or systemic fungicide" -- never a specific product, brand,
    # or dose (app.disease_recommendations.registry.CHEMICAL_WITHHELD policy).
    # Null for a healthy result or when no category-level text was produced.
    conventional_category_english: Mapped[str | None] = mapped_column(Text)
    conventional_category_tamil: Mapped[str | None] = mapped_column(Text)
    visible_parts: Mapped[list | None] = mapped_column(JSON)
    needs_expert_review: Mapped[bool] = mapped_column(Boolean, default=False)
    review_status: Mapped[str | None] = mapped_column(String(20), index=True)
    reviewer_role: Mapped[str | None] = mapped_column(String(30))
    corrected_label: Mapped[str | None] = mapped_column(String(120))
    review_timestamp: Mapped[datetime | None] = mapped_column()
    review_consent: Mapped[bool | None] = mapped_column(Boolean)
    kvk_session: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

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

    @property
    def test_mode(self) -> dict | None:
        """Expose controlled-test provenance without exposing the full raw result."""
        if not isinstance(self.raw_response, dict):
            return None
        marker = self.raw_response.get("test_mode")
        return marker if isinstance(marker, dict) else None

    @property
    def verification_level(self) -> str | None:
        """Whether this report was confirmed by a trained local classifier or
        is an OpenAI-vision-only estimate (docs/AI_DECISION_MATRIX.md ->
        DISEASE DETECTION). The general farmer-diagnosis path
        (app.modules.disease.farmer_diagnosis_service) always shows OpenAI's
        natural-language read to the farmer, but that read is only backed by
        a purpose-trained, calibrated classifier when one exists for the crop
        AND it independently agrees. The frontend must not present these two
        cases with equal visual confidence -- this field is the single source
        of truth for that distinction, derived from the same `local_model`
        block the diagnosis service already persists on every farmer report.
        Returns None for controlled-tester reports (banana_v3 / restricted /
        legacy_joint direct calls), which don't set this raw_response shape
        and aren't shown through the general-diagnosis screen anyway.
        """
        if not isinstance(self.raw_response, dict):
            return None
        local_model = self.raw_response.get("local_model")
        if not isinstance(local_model, dict):
            return None
        if local_model.get("label") is not None and local_model.get("agreement") is True:
            return "verified_by_local_model"
        return "ai_vision_estimate"
