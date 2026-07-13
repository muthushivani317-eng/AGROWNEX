"""Soil Intelligence ORM models (docs: future-ready soil engine).

Normalized tables:

* ``soil_profiles``        — the current best-known soil state per farm (a merged
  snapshot of the latest values + source + confidence). Values are ``None`` when
  unavailable — never fabricated (docs/PRODUCT_RULES.md).
* ``soil_reports``         — each uploaded/received report (farmer card, lab,
  government dataset, satellite). Stores the R2/S3 URL + metadata only.
* ``soil_test_results``    — the measured values that belong to one report.
* ``soil_recommendations`` — deterministic, *generic* agronomic advice generated
  by the Soil Engine (localization codes; no brands).
* ``soil_history``         — an immutable trend snapshot per processed report.

``user_id`` is the farmer (FK ``users.id``), matching every module.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.soil.constants import ReportStatus, SoilSource
from app.shared.base_model import (
    GUID,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)


class SoilProfile(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "soil_profiles"
    __table_args__ = (
        UniqueConstraint("farm_id", name="uq_soil_profiles_farm"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True, nullable=False
    )

    soil_type: Mapped[str | None] = mapped_column(String(60))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    ph: Mapped[float | None] = mapped_column(Float)
    organic_carbon: Mapped[float | None] = mapped_column(Float)
    nitrogen: Mapped[float | None] = mapped_column(Float)
    phosphorus: Mapped[float | None] = mapped_column(Float)
    potassium: Mapped[float | None] = mapped_column(Float)
    micronutrients: Mapped[dict | None] = mapped_column(JSON)
    ec_salinity: Mapped[float | None] = mapped_column(Float)
    water_holding_capacity: Mapped[float | None] = mapped_column(Float)
    drainage: Mapped[str | None] = mapped_column(String(20))

    source: Mapped[str] = mapped_column(
        String(24), default=SoilSource.SELF.value, nullable=False
    )
    confidence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_test_date: Mapped[date | None] = mapped_column(Date)


class SoilReport(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "soil_reports"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True, nullable=False
    )
    source: Mapped[str] = mapped_column(
        String(24), default=SoilSource.SELF.value, nullable=False, index=True
    )
    report_url: Mapped[str | None] = mapped_column(String(512))
    thumbnail_url: Mapped[str | None] = mapped_column(String(512))
    mime_type: Mapped[str | None] = mapped_column(String(80))
    lab_name: Mapped[str | None] = mapped_column(String(160))
    test_date: Mapped[date | None] = mapped_column(Date, index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(12), default=ReportStatus.SUBMITTED.value, nullable=False, index=True
    )
    confidence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    result: Mapped[SoilTestResult | None] = relationship(
        back_populates="report",
        lazy="selectin",
        cascade="all, delete-orphan",
        uselist=False,
    )


class SoilTestResult(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "soil_test_results"

    report_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("soil_reports.id"), index=True, nullable=False
    )
    ph: Mapped[float | None] = mapped_column(Float)
    organic_carbon: Mapped[float | None] = mapped_column(Float)
    nitrogen: Mapped[float | None] = mapped_column(Float)
    phosphorus: Mapped[float | None] = mapped_column(Float)
    potassium: Mapped[float | None] = mapped_column(Float)
    sulphur: Mapped[float | None] = mapped_column(Float)
    ec_salinity: Mapped[float | None] = mapped_column(Float)
    water_holding_capacity: Mapped[float | None] = mapped_column(Float)
    drainage: Mapped[str | None] = mapped_column(String(20))
    micronutrients: Mapped[dict | None] = mapped_column(JSON)

    report: Mapped[SoilReport] = relationship(back_populates="result")


class SoilRecommendation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "soil_recommendations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True, nullable=False
    )
    report_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("soil_reports.id"), index=True
    )
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    parameter: Mapped[str | None] = mapped_column(String(30))
    rating: Mapped[str | None] = mapped_column(String(20))
    severity: Mapped[str] = mapped_column(String(12), nullable=False)
    priority: Mapped[str] = mapped_column(String(12), nullable=False)
    value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(12))


class SoilHistory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "soil_history"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True, nullable=False
    )
    report_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("soil_reports.id"), index=True
    )
    test_date: Mapped[date | None] = mapped_column(Date, index=True)
    ph: Mapped[float | None] = mapped_column(Float)
    organic_carbon: Mapped[float | None] = mapped_column(Float)
    nitrogen: Mapped[float | None] = mapped_column(Float)
    phosphorus: Mapped[float | None] = mapped_column(Float)
    potassium: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(24), nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
