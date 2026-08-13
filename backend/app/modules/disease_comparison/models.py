from __future__ import annotations

import uuid

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import GUID, Base, TimestampMixin, UUIDMixin


class DiseaseModelComparison(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "disease_model_comparisons"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    image_sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    crop: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    local_model: Mapped[str] = mapped_column(String(120), nullable=False)
    local_status: Mapped[str] = mapped_column(String(40), nullable=False)
    local_label: Mapped[str | None] = mapped_column(String(120))
    local_confidence: Mapped[float | None] = mapped_column(Float)

    provider: Mapped[str] = mapped_column(String(40), default="openai", nullable=False)
    provider_model: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_status: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    provider_label: Mapped[str | None] = mapped_column(String(120))
    crop_assessment: Mapped[str | None] = mapped_column(String(20))
    assessment_status: Mapped[str | None] = mapped_column(String(24))
    alternative_labels: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    visual_observations: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    agrees_with_local: Mapped[bool | None] = mapped_column(Boolean)
    error_code: Mapped[str | None] = mapped_column(String(80))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    test_mode: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    exposed_to_farmer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
