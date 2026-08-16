from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import GUID, Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class CommunityQuestion(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "community_questions"
    author_user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    crop: Mapped[str | None] = mapped_column(String(80), index=True)
    language: Mapped[str] = mapped_column(String(8), default="ta", nullable=False)
    moderation_status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    report_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class CommunityAnswer(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "community_answers"
    question_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("community_questions.id", ondelete="CASCADE"), index=True
    )
    author_user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(8), default="ta", nullable=False)
    moderation_status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    report_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class CommunityReport(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "community_reports"
    __table_args__ = (
        UniqueConstraint(
            "reporter_user_id", "target_type", "target_id", name="uq_community_report"
        ),
    )
    reporter_user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), index=True)
    target_type: Mapped[str] = mapped_column(String(12), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(GUID(), index=True, nullable=False)
    reason: Mapped[str] = mapped_column(String(40), nullable=False)
