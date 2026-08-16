"""Farm ORM models (docs/DATABASE_SCHEMA.md → Farm domain).

Tables: farms · farm_locations · farm_boundaries · farm_media.

Geometry is stored as GeoJSON in a JSON column (JSONB on PostgreSQL) — the
PostGIS-compatible interchange format — alongside derived numeric columns (area,
perimeter, centroid) for fast listing/filtering. A native ``geometry`` column can
be added later as an additive migration without redesign.
"""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import (
    JSON,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.farms.constants import AreaSource, FarmStatus
from app.shared.base_model import (
    GUID,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)


class Farm(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A registered farm (docs/DATABASE_SCHEMA.md → farms)."""

    __tablename__ = "farms"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    crop: Mapped[str | None] = mapped_column(String(80), index=True)
    crop_variety: Mapped[str | None] = mapped_column(String(120))
    sowing_date: Mapped[date | None] = mapped_column()
    soil_type: Mapped[str | None] = mapped_column(String(40))
    irrigation_type: Mapped[str | None] = mapped_column(String(40))
    water_source: Mapped[str | None] = mapped_column(String(40))
    # Effective area (hectares): computed from the boundary, or a manual override.
    area_hectares: Mapped[float | None] = mapped_column(Float)
    area_source: Mapped[str] = mapped_column(
        String(10), default=AreaSource.AUTO.value, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20), default=FarmStatus.ACTIVE.value, nullable=False, index=True
    )

    location: Mapped[FarmLocation | None] = relationship(
        back_populates="farm",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    boundary: Mapped[FarmBoundary | None] = relationship(
        back_populates="farm",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    media: Mapped[list[FarmMedia]] = relationship(
        back_populates="farm",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="FarmMedia.created_at",
    )


class FarmLocation(UUIDMixin, TimestampMixin, Base):
    """GPS location + administrative area (docs/DATABASE_SCHEMA.md → farm_locations)."""

    __tablename__ = "farm_locations"

    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), unique=True, index=True, nullable=False
    )
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    accuracy: Mapped[float | None] = mapped_column(Float)
    elevation: Mapped[float | None] = mapped_column(Float)
    address: Mapped[str | None] = mapped_column(String(255))
    district: Mapped[str | None] = mapped_column(String(80), index=True)
    block: Mapped[str | None] = mapped_column(String(80), index=True)
    village: Mapped[str | None] = mapped_column(String(80), index=True)
    source: Mapped[str] = mapped_column(String(10), default="gps", nullable=False)

    farm: Mapped[Farm] = relationship(back_populates="location")


class FarmBoundary(UUIDMixin, TimestampMixin, Base):
    """Polygon boundary as GeoJSON (docs/DATABASE_SCHEMA.md → farm_boundaries)."""

    __tablename__ = "farm_boundaries"

    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), unique=True, index=True, nullable=False
    )
    geojson: Mapped[dict | None] = mapped_column(JSON)
    area_hectares: Mapped[float | None] = mapped_column(Float)
    perimeter_m: Mapped[float | None] = mapped_column(Float)
    centroid_lat: Mapped[float | None] = mapped_column(Float)
    centroid_lng: Mapped[float | None] = mapped_column(Float)
    vertex_count: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(10), default="drawn", nullable=False)

    farm: Mapped[Farm] = relationship(back_populates="boundary")


class FarmMedia(UUIDMixin, TimestampMixin, Base):
    """Farm photo metadata; the file itself lives in S3 (docs/DATABASE_SCHEMA.md)."""

    __tablename__ = "farm_media"

    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True, nullable=False
    )
    file_url: Mapped[str] = mapped_column(String(512), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str | None] = mapped_column(String(80))
    file_size: Mapped[int | None] = mapped_column(Integer)
    caption: Mapped[str | None] = mapped_column(String(255))
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id")
    )

    farm: Mapped[Farm] = relationship(back_populates="media")


class FarmTeamMember(UUIDMixin, TimestampMixin, Base):
    """Controlled-test farm roster entry.

    This records coordination roles only. It deliberately does not grant access to
    the owner's farm data; shared-data permissions require a separate reviewed RBAC
    design and explicit member consent.
    """

    __tablename__ = "farm_team_members"
    __table_args__ = (
        UniqueConstraint("farm_id", "user_id", name="uq_farm_team_member"),
    )

    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    added_by: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=False
    )
