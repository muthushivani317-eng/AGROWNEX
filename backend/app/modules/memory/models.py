"""Farm Memory ORM models (docs: normalized tables; AI-ready; future vector search).

* ``farm_memories``     — one canonical, immutable memory per real farm event
  (merged from one or more raw ``memory_events``). Carries the farmer, farm, source
  module, event type, localization summary, confidence, importance, season, crop and
  location, and reserves embedding fields for future vector search.
* ``memory_events``     — the raw structured events that back a memory (append-only;
  several duplicate events roll up into one ``farm_memory``).
* ``memory_embeddings`` — RESERVED for future embeddings / vector search / RAG. No
  vector is written in V1; the row exists so the seam needs no schema redesign.
* ``memory_tags``       — free tags on a memory (crop / season / severity, etc.).
* ``memory_summaries``  — generated seasonal and yearly summaries per farm.
* ``memory_links``      — deterministic relationships between memories (follows /
  relates / resolves) — the seed of a future farm knowledge graph.

``user_id`` is the farmer (FK ``users.id``), matching every module. Source-module
data is only read — never overwritten. Historical memories are immutable.
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
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.memory.constants import Importance, ObservationKind
from app.shared.base_model import (
    GUID,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)


class FarmMemory(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "farm_memories"
    __table_args__ = (
        UniqueConstraint("user_id", "dedup_key", name="uq_farm_memory_dedup"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True, nullable=False
    )
    source_module: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    # ``summary`` is a localization code (Tamil-first client renders it with params).
    summary: Mapped[str] = mapped_column(String(80), nullable=False)
    params: Mapped[dict | None] = mapped_column(JSON)
    # English detail for future AI/RAG retrieval — never shown directly to the farmer.
    detail: Mapped[str | None] = mapped_column(String(500))
    confidence: Mapped[int | None] = mapped_column(Integer)
    importance: Mapped[str] = mapped_column(
        String(12), default=Importance.LOW.value, nullable=False
    )
    importance_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    observation: Mapped[str] = mapped_column(
        String(12), default=ObservationKind.OBSERVED.value, nullable=False
    )
    season: Mapped[str | None] = mapped_column(String(12), index=True)
    season_year: Mapped[int | None] = mapped_column(Integer, index=True)
    crop: Mapped[str | None] = mapped_column(String(80), index=True)
    location: Mapped[str | None] = mapped_column(String(160))
    source_ref: Mapped[str | None] = mapped_column(String(64))
    dedup_key: Mapped[str] = mapped_column(String(160), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    # --- Reserved for future vector search / embeddings / RAG (not used in V1) ---
    embedding_ref: Mapped[str | None] = mapped_column(String(120))
    embedding_model: Mapped[str | None] = mapped_column(String(60))

    events: Mapped[list[MemoryEvent]] = relationship(
        back_populates="memory", lazy="selectin", cascade="all, delete-orphan"
    )
    tags: Mapped[list[MemoryTag]] = relationship(
        back_populates="memory", lazy="selectin", cascade="all, delete-orphan"
    )
    embeddings: Mapped[list[MemoryEmbedding]] = relationship(
        back_populates="memory", lazy="selectin", cascade="all, delete-orphan"
    )


class MemoryEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "memory_events"

    memory_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farm_memories.id"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True, nullable=False
    )
    source_module: Mapped[str] = mapped_column(String(24), nullable=False)
    event_type: Mapped[str] = mapped_column(String(48), nullable=False)
    confidence: Mapped[int | None] = mapped_column(Integer)
    payload: Mapped[dict | None] = mapped_column(JSON)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    memory: Mapped[FarmMemory] = relationship(back_populates="events")


class MemoryEmbedding(UUIDMixin, TimestampMixin, Base):
    """RESERVED for future vector search / RAG. No vector is written in V1."""

    __tablename__ = "memory_embeddings"

    memory_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farm_memories.id"), index=True, nullable=False
    )
    provider: Mapped[str | None] = mapped_column(String(40))
    model: Mapped[str | None] = mapped_column(String(60))
    dimensions: Mapped[int | None] = mapped_column(Integer)
    vector: Mapped[list | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)

    memory: Mapped[FarmMemory] = relationship(back_populates="embeddings")


class MemoryTag(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "memory_tags"
    __table_args__ = (
        UniqueConstraint("memory_id", "tag", name="uq_memory_tag"),
    )

    memory_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farm_memories.id"), index=True, nullable=False
    )
    tag: Mapped[str] = mapped_column(String(48), nullable=False, index=True)

    memory: Mapped[FarmMemory] = relationship(back_populates="tags")


class MemorySummary(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "memory_summaries"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "farm_id", "period_type", "period_key",
            name="uq_memory_summary_period",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True, nullable=False
    )
    period_type: Mapped[str] = mapped_column(String(8), nullable=False)  # season | year
    period_key: Mapped[str] = mapped_column(String(24), nullable=False)  # 2026-kharif
    season: Mapped[str | None] = mapped_column(String(12))
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    crop: Mapped[str | None] = mapped_column(String(80))
    summary: Mapped[str] = mapped_column(String(80), nullable=False)  # localization code
    params: Mapped[dict | None] = mapped_column(JSON)
    highlights: Mapped[list | None] = mapped_column(JSON)  # top memory ids/codes
    event_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    importance: Mapped[str] = mapped_column(String(12), default="low", nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class MemoryLink(UUIDMixin, TimestampMixin, Base):
    """A deterministic relationship between two memories (future knowledge graph)."""

    __tablename__ = "memory_links"
    __table_args__ = (
        UniqueConstraint(
            "from_memory_id", "to_memory_id", "link_type", name="uq_memory_link"
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    from_memory_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farm_memories.id"), index=True, nullable=False
    )
    to_memory_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("farm_memories.id"), index=True, nullable=False
    )
    link_type: Mapped[str] = mapped_column(String(16), nullable=False)
