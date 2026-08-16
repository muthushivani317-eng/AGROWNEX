"""Scheme ORM models (docs/DATABASE_SCHEMA.md → Government domain).

Three tables:

* ``government_schemes`` — verified schemes, with descriptive fields *and* the
  structured eligibility rules the engine evaluates (districts/crops/land/income/
  category). Only verified schemes are stored (docs: never fabricate).
* ``scheme_documents``   — the required-document checklist per scheme.
* ``scheme_bookmarks``   — a farmer's saved schemes (user-scoped).

The docs list free-text ``eligibility``; the engine additionally needs machine
rules, so structured columns are stored alongside the human-readable summary.
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
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.schemes.constants import SchemeCategory, SchemeStatus
from app.shared.base_model import (
    GUID,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)


class GovernmentScheme(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "government_schemes"

    # Stable identity from the source, for idempotent upserts across refreshes.
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(
        String(30), default=SchemeCategory.OTHER.value, nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    benefits: Mapped[str | None] = mapped_column(Text)
    # Human-readable eligibility summary (docs) + machine rules (below).
    eligibility_summary: Mapped[str | None] = mapped_column(Text)
    application_steps: Mapped[list | None] = mapped_column(JSON)
    departments: Mapped[list | None] = mapped_column(JSON)

    official_url: Mapped[str | None] = mapped_column(String(512))
    state: Mapped[str] = mapped_column(String(80), default="all", nullable=False, index=True)
    start_date: Mapped[date | None] = mapped_column(Date)
    last_date: Mapped[date | None] = mapped_column(Date)

    status: Mapped[str] = mapped_column(
        String(12), default=SchemeStatus.ACTIVE.value, nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # --- Structured eligibility rules (evaluated by the engine) ---
    # Each list uses ["all"] to mean "no constraint".
    states: Mapped[list | None] = mapped_column(JSON)
    districts: Mapped[list | None] = mapped_column(JSON)
    crops: Mapped[list | None] = mapped_column(JSON)
    farmer_categories: Mapped[list | None] = mapped_column(JSON)
    min_land_hectares: Mapped[float | None] = mapped_column(Float)
    max_land_hectares: Mapped[float | None] = mapped_column(Float)
    max_annual_income: Mapped[int | None] = mapped_column(Integer)


class SchemeDocument(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "scheme_documents"

    scheme_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("government_schemes.id"), index=True, nullable=False
    )
    document_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class FarmerDocument(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "farmer_documents"
    __table_args__ = (
        UniqueConstraint("user_id", "document_type", name="uq_farmer_document_type"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    document_type: Mapped[str] = mapped_column(String(40), nullable=False)
    has_document: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class SchemeBookmark(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "scheme_bookmarks"
    __table_args__ = (
        UniqueConstraint("user_id", "scheme_id", name="uq_scheme_bookmark"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    scheme_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("government_schemes.id"), index=True, nullable=False
    )
