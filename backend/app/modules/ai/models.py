"""AI Chat ORM models (docs/DATABASE_SCHEMA.md → AI Memory domain).

Tables: ai_conversations · ai_messages. Conversations are user-scoped and may
optionally reference a farm (crop-session linkage arrives with Crop Management).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.ai.constants import DEFAULT_LANGUAGE
from app.shared.base_model import (
    GUID,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)


class AIConversation(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A chat session (docs/DATABASE_SCHEMA.md → ai_conversations)."""

    __tablename__ = "ai_conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    farm_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("farms.id"), index=True
    )
    # Crop-session linkage is reserved; the table does not exist yet.
    crop_session_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    title: Mapped[str | None] = mapped_column(String(120))
    language: Mapped[str] = mapped_column(
        String(5), default=DEFAULT_LANGUAGE, nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    messages: Mapped[list[AIMessage]] = relationship(
        back_populates="conversation",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="AIMessage.created_at",
    )


class AIMessage(UUIDMixin, TimestampMixin, Base):
    """One message in a conversation (docs/DATABASE_SCHEMA.md → ai_messages)."""

    __tablename__ = "ai_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("ai_conversations.id"), index=True, nullable=False
    )
    sender: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(5), default=DEFAULT_LANGUAGE)
    model_used: Mapped[str | None] = mapped_column(String(60))
    token_count: Mapped[int | None] = mapped_column(Integer)

    conversation: Mapped[AIConversation] = relationship(back_populates="messages")


class TokenUsage(UUIDMixin, TimestampMixin, Base):
    """Per-request AI token usage & estimated cost (Phase 1 — cost control).

    One row per model call across the whole platform (chat, disease vision, …) so
    the admin cost dashboard can aggregate real spend per model and per module.
    ``farmer_id`` is nullable so anonymous/system calls are still accounted for.
    Token counts may be ``None`` when a provider does not report usage (e.g. the
    offline mock) — in that case the estimated cost is ``0`` and never fabricated.
    """

    __tablename__ = "token_usage"

    farmer_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=True
    )
    module: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(20), nullable=False, default="gemini")
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    estimated_cost_inr: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    is_sample: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
