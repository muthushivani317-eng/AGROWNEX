"""Nutrient Deficiency ORM models (docs: normalized tables).

* ``nutrient_reports``         — one analysed crop photo (R2 URL + context + the
  provider/model that produced it). Cross-module references (soil/satellite/weather)
  are frozen on the report at analysis time.
* ``nutrient_analysis``        — the engine's verdict for a report (primary/secondary
  deficiency, status, adjusted confidence, severity, evidence flags). A missing or
  unconfirmed value is honest — never fabricated (docs/PRODUCT_RULES.md).
* ``nutrient_symptoms``        — the visible leaf symptoms observed for a report.
* ``nutrient_recommendations`` — deterministic, *generic* agronomic advice (codes;
  no commercial brands).
* ``nutrient_history``         — an immutable trend snapshot per analysed report.

``user_id`` is the farmer (FK ``users.id``), matching every module.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.nutrient.constants import DEFAULT_LANGUAGE, ReportStatus
from app.shared.base_model import (
    GUID,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)


class NutrientReport(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "nutrient_reports"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True, nullable=False
    )
    crop: Mapped[str | None] = mapped_column(String(80), index=True)

    image_url: Mapped[str] = mapped_column(String(512), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(512))
    capture_method: Mapped[str] = mapped_column(String(20), default="gallery")
    capture_date: Mapped[date | None] = mapped_column(Date, index=True)

    provider: Mapped[str] = mapped_column(String(24), nullable=False)
    model_used: Mapped[str | None] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(
        String(12), default=ReportStatus.ANALYZED.value, nullable=False, index=True
    )
    language: Mapped[str] = mapped_column(String(5), default=DEFAULT_LANGUAGE, nullable=False)

    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    # Frozen cross-module context (never fabricated; null when a module has no data).
    weather_snapshot: Mapped[dict | None] = mapped_column(JSON)
    raw_response: Mapped[dict | None] = mapped_column(JSON)

    analysis: Mapped[NutrientAnalysis | None] = relationship(
        back_populates="report",
        lazy="selectin",
        cascade="all, delete-orphan",
        uselist=False,
    )
    symptoms: Mapped[list[NutrientSymptom]] = relationship(
        back_populates="report",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    recommendations: Mapped[list[NutrientRecommendation]] = relationship(
        back_populates="report",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class NutrientAnalysis(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "nutrient_analysis"

    report_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("nutrient_reports.id"), index=True, nullable=False
    )
    primary_deficiency: Mapped[str | None] = mapped_column(String(20))
    secondary_deficiency: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    severity: Mapped[str] = mapped_column(String(12), nullable=False)
    affected_area: Mapped[str | None] = mapped_column(String(16))

    # Corroboration evidence (transparent; JSON snapshots of the source signals).
    soil_reference: Mapped[dict | None] = mapped_column(JSON)
    satellite_reference: Mapped[dict | None] = mapped_column(JSON)
    weather_reference: Mapped[dict | None] = mapped_column(JSON)
    disease_conflict: Mapped[bool] = mapped_column(Boolean, default=False)

    needs_test: Mapped[bool] = mapped_column(Boolean, default=False)
    needs_expert: Mapped[bool] = mapped_column(Boolean, default=False)

    explanation_tamil: Mapped[str | None] = mapped_column(Text)
    explanation_english: Mapped[str | None] = mapped_column(Text)

    report: Mapped[NutrientReport] = relationship(back_populates="analysis")


class NutrientSymptom(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "nutrient_symptoms"

    report_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("nutrient_reports.id"), index=True, nullable=False
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    label: Mapped[str | None] = mapped_column(String(160))

    report: Mapped[NutrientReport] = relationship(back_populates="symptoms")


class NutrientRecommendation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "nutrient_recommendations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True, nullable=False
    )
    report_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("nutrient_reports.id"), index=True
    )
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    nutrient: Mapped[str | None] = mapped_column(String(20))
    severity: Mapped[str] = mapped_column(String(12), nullable=False)
    priority: Mapped[str] = mapped_column(String(12), nullable=False)

    report: Mapped[NutrientReport | None] = relationship(back_populates="recommendations")


class NutrientHistory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "nutrient_history"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True, nullable=False
    )
    report_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("nutrient_reports.id"), index=True
    )
    crop: Mapped[str | None] = mapped_column(String(80))
    primary_deficiency: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    severity: Mapped[str | None] = mapped_column(String(12))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
