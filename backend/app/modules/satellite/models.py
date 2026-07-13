"""Satellite Intelligence ORM models (docs: future-ready satellite monitoring).

Normalized tables:

* ``satellite_sessions``  — one monitoring pass per farm. Holds the summary indices
  + classifications, the provider, cloud cover, and an honest availability status /
  reason (values are ``None`` when a scene is unavailable — never fabricated).
* ``satellite_images``    — rendered layers (true-colour / NDVI / NDMI …) stored in
  R2/S3; the DB keeps only the URL + metadata.
* ``satellite_indices``   — per-index detail (mean/min/max/std) for a session,
  supporting field-variation detection.
* ``satellite_alerts``    — deterministic alerts raised by the alert engine.
* ``satellite_history``   — an immutable trend snapshot per available session.

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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.satellite.constants import (
    SessionStatus,
    UnavailableReason,
)
from app.shared.base_model import (
    GUID,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)


class SatelliteSession(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "satellite_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True, nullable=False
    )

    provider: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(
        String(12), default=SessionStatus.PENDING.value, nullable=False, index=True
    )
    unavailable_reason: Mapped[str] = mapped_column(
        String(20), default=UnavailableReason.NONE.value, nullable=False
    )
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    capture_date: Mapped[date | None] = mapped_column(Date, index=True)
    cloud_cover: Mapped[float | None] = mapped_column(Float)
    resolution_m: Mapped[float | None] = mapped_column(Float)

    # Summary vegetation indices (field means) — null when unavailable.
    ndvi: Mapped[float | None] = mapped_column(Float)
    ndre: Mapped[float | None] = mapped_column(Float)
    evi: Mapped[float | None] = mapped_column(Float)
    ndmi: Mapped[float | None] = mapped_column(Float)

    vegetation_health: Mapped[str | None] = mapped_column(String(12))
    stress_level: Mapped[str | None] = mapped_column(String(12))
    moisture_status: Mapped[str | None] = mapped_column(String(12))
    trend: Mapped[str | None] = mapped_column(String(12))
    ndvi_delta: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    session_metadata: Mapped[dict | None] = mapped_column("metadata", JSON)

    images: Mapped[list[SatelliteImage]] = relationship(
        back_populates="session",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    indices: Mapped[list[SatelliteIndex]] = relationship(
        back_populates="session",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    alerts: Mapped[list[SatelliteAlert]] = relationship(
        back_populates="session",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="SatelliteAlert.created_at",
    )


class SatelliteImage(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "satellite_images"

    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("satellite_sessions.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True, nullable=False
    )
    band: Mapped[str] = mapped_column(String(16), nullable=False)
    image_url: Mapped[str] = mapped_column(String(512), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(512))
    mime_type: Mapped[str | None] = mapped_column(String(80))
    resolution_m: Mapped[float | None] = mapped_column(Float)

    session: Mapped[SatelliteSession] = relationship(back_populates="images")


class SatelliteIndex(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "satellite_indices"

    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("satellite_sessions.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True, nullable=False
    )
    index_name: Mapped[str] = mapped_column(String(8), nullable=False)
    mean: Mapped[float | None] = mapped_column(Float)
    minimum: Mapped[float | None] = mapped_column(Float)
    maximum: Mapped[float | None] = mapped_column(Float)
    std: Mapped[float | None] = mapped_column(Float)

    session: Mapped[SatelliteSession] = relationship(back_populates="indices")


class SatelliteAlert(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "satellite_alerts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("satellite_sessions.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True, nullable=False
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    severity: Mapped[str] = mapped_column(String(12), nullable=False)
    priority: Mapped[str] = mapped_column(String(12), nullable=False)
    value: Mapped[float | None] = mapped_column(Float)
    params: Mapped[dict | None] = mapped_column(JSON)

    session: Mapped[SatelliteSession] = relationship(back_populates="alerts")


class SatelliteHistory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "satellite_history"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True, nullable=False
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("satellite_sessions.id"), index=True
    )
    capture_date: Mapped[date | None] = mapped_column(Date, index=True)
    ndvi: Mapped[float | None] = mapped_column(Float)
    ndre: Mapped[float | None] = mapped_column(Float)
    evi: Mapped[float | None] = mapped_column(Float)
    ndmi: Mapped[float | None] = mapped_column(Float)
    vegetation_health: Mapped[str | None] = mapped_column(String(12))
    stress_level: Mapped[str | None] = mapped_column(String(12))
    moisture_status: Mapped[str | None] = mapped_column(String(12))
    source: Mapped[str] = mapped_column(String(24), nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
