"""Crop Intelligence ORM models (docs: normalized tables).

* ``crop_intelligence_reports`` — one aggregated farm-health report per refresh
  (overall health, confidence, overall risk, the modules that contributed).
* ``crop_health_scores``        — the per-module health sub-scores for a report
  (``None`` when a module had no data — never fabricated).
* ``crop_risk_scores``          — the risk level + ranked priority issues.
* ``crop_recommendations``      — the prioritized generic recommendations (codes).
* ``crop_decision_history``     — an immutable trend snapshot per report.

``user_id`` is the farmer (FK ``users.id``), matching every module. Source-module
data is only read — never overwritten.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.intelligence.constants import RiskLevel
from app.shared.base_model import (
    GUID,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)


class CropIntelligenceReport(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "crop_intelligence_reports"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True, nullable=False
    )
    crop: Mapped[str | None] = mapped_column(String(80))
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    overall_health_score: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    overall_risk: Mapped[str] = mapped_column(
        String(12), default=RiskLevel.LOW.value, nullable=False
    )
    sources_used: Mapped[list | None] = mapped_column(JSON)

    health: Mapped[CropHealthScore | None] = relationship(
        back_populates="report", lazy="selectin", cascade="all, delete-orphan", uselist=False
    )
    risk: Mapped[CropRiskScore | None] = relationship(
        back_populates="report", lazy="selectin", cascade="all, delete-orphan", uselist=False
    )
    recommendations: Mapped[list[CropRecommendation]] = relationship(
        back_populates="report", lazy="selectin", cascade="all, delete-orphan"
    )


class CropHealthScore(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "crop_health_scores"

    report_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("crop_intelligence_reports.id"), index=True, nullable=False
    )
    overall_health_score: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    disease_score: Mapped[int | None] = mapped_column(Integer)
    nutrient_score: Mapped[int | None] = mapped_column(Integer)
    soil_score: Mapped[int | None] = mapped_column(Integer)
    satellite_score: Mapped[int | None] = mapped_column(Integer)
    weather_score: Mapped[int | None] = mapped_column(Integer)
    growth_score: Mapped[int | None] = mapped_column(Integer)

    report: Mapped[CropIntelligenceReport] = relationship(back_populates="health")


class CropRiskScore(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "crop_risk_scores"

    report_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("crop_intelligence_reports.id"), index=True, nullable=False
    )
    overall_risk: Mapped[str] = mapped_column(String(12), nullable=False)
    risk_score: Mapped[int | None] = mapped_column(Integer)
    priority_issues: Mapped[list | None] = mapped_column(JSON)

    report: Mapped[CropIntelligenceReport] = relationship(back_populates="risk")


class CropRecommendation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "crop_recommendations"

    report_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("crop_intelligence_reports.id"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True, nullable=False
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    priority: Mapped[str] = mapped_column(String(12), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    modules: Mapped[list | None] = mapped_column(JSON)
    rank: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    report: Mapped[CropIntelligenceReport | None] = relationship(
        back_populates="recommendations"
    )


class CropDecisionHistory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "crop_decision_history"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True, nullable=False
    )
    report_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("crop_intelligence_reports.id"), index=True
    )
    overall_health_score: Mapped[int | None] = mapped_column(Integer)
    overall_risk: Mapped[str] = mapped_column(String(12), nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
