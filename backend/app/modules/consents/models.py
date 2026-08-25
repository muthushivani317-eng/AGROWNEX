from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, event, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import GUID, Base, UUIDMixin


class UserConsentEvent(UUIDMixin, Base):
    """Immutable consent decision for an authenticated user."""

    __tablename__ = "user_consent_events"
    __table_args__ = (
        UniqueConstraint("user_id", "purpose", "version", name="uq_consent_user_purpose_version"),
        UniqueConstraint("user_id", "purpose", "idempotency_key", name="uq_consent_idempotency"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(80), nullable=False)
    notice_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    locale: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


def _reject_mutation(*_args, **_kwargs) -> None:
    raise ValueError("CONSENT_EVENT_IMMUTABLE")


event.listen(UserConsentEvent, "before_update", _reject_mutation)
event.listen(UserConsentEvent, "before_delete", _reject_mutation)


class UserConsentState(Base):
    __tablename__ = "user_consent_states"
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), primary_key=True)
    purpose: Mapped[str] = mapped_column(String(40), primary_key=True)
    last_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
