"""Role-Based Access Control models (docs/DATABASE_SCHEMA.md → Authorization).

Preparation only for this module — roles are seeded and users default to
`farmer`; enforcement middleware arrives with the admin/FPO features.
"""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import GUID, Base, TimestampMixin, UUIDMixin


class Role(UUIDMixin, TimestampMixin, Base):
    """Role master (docs/DATABASE_SCHEMA.md → roles)."""

    __tablename__ = "roles"

    role_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))


class Permission(UUIDMixin, TimestampMixin, Base):
    """Permission master (docs/DATABASE_SCHEMA.md → permissions)."""

    __tablename__ = "permissions"

    permission_name: Mapped[str] = mapped_column(
        String(80), unique=True, nullable=False
    )
    description: Mapped[str | None] = mapped_column(String(255))


class RolePermission(UUIDMixin, TimestampMixin, Base):
    """Role→permission assignment (docs/DATABASE_SCHEMA.md → role_permissions)."""

    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )

    role_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("roles.id"), index=True, nullable=False
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("permissions.id"), index=True, nullable=False
    )


class UserRole(UUIDMixin, TimestampMixin, Base):
    """User→role assignment (docs/DATABASE_SCHEMA.md → user_roles)."""

    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), index=True, nullable=False
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("roles.id"), index=True, nullable=False
    )
