"""Idempotent seeding for the admin platform (roles, permissions, widgets).

Also exposes ``ensure_admin`` to promote an authenticated user to an admin — the
bootstrap path used to create the first Super Admin (and by tests). Seeding is safe to
run repeatedly (upsert by natural key).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.admin.constants import (
    DEFAULT_WIDGETS,
    AdminPermission,
    AdminRole,
    AdminUserStatus,
)
from app.modules.admin.models import (
    AdminPermissionModel,
    AdminRoleModel,
    AdminUser,
    DashboardWidget,
)


async def seed_admin_reference(session: AsyncSession) -> None:
    """Seed admin roles, permissions and dashboard widgets (idempotent)."""
    existing_roles = {
        r for r in (await session.execute(select(AdminRoleModel.name))).scalars().all()
    }
    for role in AdminRole:
        if role.value not in existing_roles:
            session.add(AdminRoleModel(name=role.value, is_system=True))

    existing_perms = {
        p for p in (await session.execute(select(AdminPermissionModel.code))).scalars().all()
    }
    for perm in AdminPermission:
        if perm.value not in existing_perms:
            session.add(AdminPermissionModel(code=perm.value))

    existing_widgets = {
        w for w in (await session.execute(select(DashboardWidget.key))).scalars().all()
    }
    for key, title_key, widget_type, order in DEFAULT_WIDGETS:
        if key not in existing_widgets:
            session.add(
                DashboardWidget(
                    key=key,
                    title_key=title_key,
                    widget_type=widget_type,
                    display_order=order,
                )
            )
    await session.flush()


async def ensure_admin(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    role: str = AdminRole.SUPER_ADMIN.value,
    full_name: str | None = None,
    email: str | None = None,
) -> AdminUser:
    """Promote a user to an admin (idempotent). Bootstraps the first Super Admin."""
    await seed_admin_reference(session)
    existing = (
        await session.execute(select(AdminUser).where(AdminUser.user_id == user_id))
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    admin = AdminUser(
        user_id=user_id,
        role=role,
        full_name=full_name,
        email=email,
        status=AdminUserStatus.ACTIVE.value,
    )
    session.add(admin)
    await session.flush()
    return admin
