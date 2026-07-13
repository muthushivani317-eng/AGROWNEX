"""SQLAlchemy declarative base and common mixins.

Enforces the database conventions from docs/DATABASE_SCHEMA.md:
UUID primary keys, created/updated/deleted timestamps, and soft deletes.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CHAR, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class GUID(TypeDecorator):
    """Platform-independent UUID.

    Uses PostgreSQL's native UUID in production, and CHAR(32) hex elsewhere
    (e.g. SQLite in tests) — behaviour is identical to native UUID on Postgres.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):  # noqa: ANN001, ANN201
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PGUUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):  # noqa: ANN001, ANN201
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        return uuid.UUID(str(value)).hex if not isinstance(value, uuid.UUID) else value.hex

    def process_result_value(self, value, dialect):  # noqa: ANN001, ANN201
        if value is None:
            return None
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


class Base(DeclarativeBase):
    """Root declarative base for all ORM models."""


class UUIDMixin:
    """UUID primary key — never auto-increment integers (docs/DATABASE_SCHEMA.md)."""

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Soft delete — production records are marked, not removed."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
