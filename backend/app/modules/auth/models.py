"""Identity, session & audit ORM models (docs/DATABASE_SCHEMA.md → User Domain).

Covers authentication and session tracking:
users · otp_requests · refresh_tokens · user_sessions · login_history.
RBAC tables live in `rbac_models.py`; profile tables in `profile_models.py`.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, FetchedValue, ForeignKey, Integer, String, event
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.auth.constants import UserStatus
from app.shared.base_model import (
    GUID,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)


class User(UUIDMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Every authenticated user (docs/DATABASE_SCHEMA.md → TABLE : users)."""

    __tablename__ = "users"

    farmer_ref: Mapped[str] = mapped_column(
        String(24), unique=True, index=True, nullable=False, server_default=FetchedValue()
    )

    firebase_uid: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    phone_number: Mapped[str | None] = mapped_column(String(20), index=True)
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    is_phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(
        String(30), default=UserStatus.ACTIVE, nullable=False
    )
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


@event.listens_for(User, "before_insert")
def _sqlite_farmer_ref(_mapper, connection, target: User) -> None:  # noqa: ANN001
    """Production uses the PostgreSQL sequence; tests need a portable fallback."""
    if connection.dialect.name != "postgresql" and not target.farmer_ref:
        target.id = target.id or uuid.uuid4()
        target.farmer_ref = f"AGF-{target.id.int % 1_000_000_000:09d}"


class OtpRequest(UUIDMixin, TimestampMixin, Base):
    """OTP verification audit & throttle (docs/DATABASE_SCHEMA.md → otp_requests).

    Firebase dispatches the SMS on-device, so no raw code is ever held server
    side; this row provides rate-limiting, attempt tracking, and an audit trail.
    `otp_hash` is nullable and, when set, is only a salted request fingerprint —
    never a recoverable OTP (docs/SECURITY.md).
    """

    __tablename__ = "otp_requests"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True
    )
    phone_number: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    otp_hash: Mapped[str | None] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class RefreshToken(UUIDMixin, TimestampMixin, Base):
    """Server-side refresh token (docs/DATABASE_SCHEMA.md → refresh_tokens).

    Only the hash is stored; rotation revokes the previous token.
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    device_id: Mapped[str | None] = mapped_column(String(128))
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class UserSession(UUIDMixin, TimestampMixin, Base):
    """Logged-in device tracking (docs/DATABASE_SCHEMA.md → user_sessions)."""

    __tablename__ = "user_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    device_name: Mapped[str | None] = mapped_column(String(120))
    device_type: Mapped[str | None] = mapped_column(String(40))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    location: Mapped[str | None] = mapped_column(String(120))
    last_active: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class LoginHistory(UUIDMixin, TimestampMixin, Base):
    """Audit log of login activity (docs/DATABASE_SCHEMA.md → login_history)."""

    __tablename__ = "login_history"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True
    )
    login_method: Mapped[str] = mapped_column(String(20), nullable=False)
    device: Mapped[str | None] = mapped_column(String(120))
    platform: Mapped[str | None] = mapped_column(String(40))
    ip: Mapped[str | None] = mapped_column(String(64))
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
