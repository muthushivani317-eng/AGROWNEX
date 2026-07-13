"""Auth dependency injection (docs/BACKEND_ARCHITECTURE.md → Dependency Injection).

Wires request → repository → service, and resolves the current authenticated
user from the Bearer token. No global singletons.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import verify_id_token
from app.modules.auth.models import User
from app.modules.auth.service import AuthService

_bearer = HTTPBearer(auto_error=True)


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthService:
    return AuthService(session)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    """Resolve and return the authenticated user for a protected route."""
    claims = verify_id_token(credentials.credentials)
    return await service.get_user_by_firebase_uid(claims["uid"])


CurrentUser = Annotated[User, Depends(get_current_user)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
