"""Admin dependency injection (docs/BACKEND_ARCHITECTURE.md → DI).

Wires request → repository → service and resolves the authenticated **admin**
context (RBAC + status check) from the current user. The client IP is captured for
the immutable audit trail (docs/SECURITY.md). No global singletons.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.admin.service import AdminContext, AdminService
from app.modules.auth.dependencies import CurrentUser

__all__ = ["AdminContextDep", "AdminServiceDep", "CurrentUser"]


def get_admin_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdminService:
    return AdminService(session)


AdminServiceDep = Annotated[AdminService, Depends(get_admin_service)]


def _client_ip(request: Request) -> str | None:
    # Honour a proxy header if present, else the direct peer (docs/DEPLOYMENT.md).
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


async def get_admin_context(
    request: Request,
    current_user: CurrentUser,
    service: AdminServiceDep,
) -> AdminContext:
    """Resolve the admin context (raises if the user is not an active admin)."""
    return await service.resolve_admin(current_user, ip_address=_client_ip(request))


AdminContextDep = Annotated[AdminContext, Depends(get_admin_context)]
