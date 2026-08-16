"""Auth dependency injection (docs/BACKEND_ARCHITECTURE.md → Dependency Injection).

Wires request → repository → service, and resolves the current authenticated
user from the Bearer token. No global singletons.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.logging import get_logger
from app.core.security import verify_id_token
from app.modules.auth.constants import RoleName, UserStatus
from app.modules.auth.models import User
from app.modules.auth.repositories import RoleRepository
from app.modules.auth.service import AuthService

_bearer = HTTPBearer(auto_error=False)
audit_logger = get_logger("crop_identity.access")


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthService:
    return AuthService(session)


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer)
    ],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    """Resolve and return the authenticated user for a protected route."""
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTHENTICATION_REQUIRED"},
        )
    claims = verify_id_token(credentials.credentials)
    user = await service.get_user_by_firebase_uid(claims["uid"])
    if user.status != UserStatus.ACTIVE or user.deleted_at is not None:
        raise UnauthorizedError(
            "Authentication is no longer active.",
            error_code="AUTHENTICATION_INVALID",
        )
    return user


CONTROLLED_TESTER_ROLES = frozenset(
    {
        RoleName.INTERNAL_TESTER.value,
        RoleName.PILOT_TESTER.value,
        RoleName.KVK_REVIEWER.value,
    }
)


@dataclass(frozen=True)
class TesterContext:
    user: User
    role: str


def require_any_role(*allowed_roles: str):
    """Return a centralized server-authoritative role dependency."""
    allowed = frozenset(allowed_roles)
    if not allowed or not allowed.issubset(CONTROLLED_TESTER_ROLES):
        raise ValueError("INVALID_CONTROLLED_ROLE_CONTRACT")

    async def dependency(
        request: Request,
        user: Annotated[User, Depends(get_current_user)],
        session: Annotated[AsyncSession, Depends(get_session)],
    ) -> TesterContext:
        subject = hashlib.sha256(str(user.id).encode()).hexdigest()[:16]
        try:
            roles = set(await RoleRepository(session).get_user_role_names(user.id))
        except Exception as exc:
            audit_logger.warning(
                "controlled_inference_access %s",
                json.dumps(
                    {
                        "subject_hash": subject,
                        "route": request.url.path,
                        "authorization_outcome": "denied",
                        "reason_code": "AUTHORIZATION_UNAVAILABLE",
                        "model_invocation_attempted": False,
                        "request_id": getattr(request.state, "request_id", ""),
                    },
                    separators=(",", ":"),
                ),
            )
            raise ForbiddenError(
                "Controlled testing authorization is unavailable.",
                error_code="AUTHORIZATION_UNAVAILABLE",
            ) from exc
        resolved = sorted(roles & allowed)
        if len(resolved) != 1:
            audit_logger.info(
                "controlled_inference_access %s",
                json.dumps(
                    {
                        "subject_hash": subject,
                        "route": request.url.path,
                        "authorization_outcome": "denied",
                        "reason_code": "TESTER_ROLE_REQUIRED",
                        "model_invocation_attempted": False,
                        "request_id": getattr(request.state, "request_id", ""),
                    },
                    separators=(",", ":"),
                ),
            )
            raise ForbiddenError(
                "Controlled tester access is required.",
                error_code="TESTER_ROLE_REQUIRED",
            )
        audit_logger.info(
            "controlled_inference_access %s",
            json.dumps(
                {
                    "subject_hash": subject,
                    "resolved_role": resolved[0],
                    "route": request.url.path,
                    "authorization_outcome": "allowed",
                    "reason_code": "CONTROLLED_TESTER_AUTHORIZED",
                    "model_invocation_attempted": False,
                    "request_id": getattr(request.state, "request_id", ""),
                },
                separators=(",", ":"),
            ),
        )
        return TesterContext(user=user, role=resolved[0])

    return dependency


def require_crop_role(crop_id: str):
    """Return the same registry-aware role boundary advertised by capabilities."""
    from app.crop_runtime.authorization import allowed_roles
    from app.crop_runtime.registry import load_registry

    return require_any_role(*allowed_roles(load_registry().get(crop_id)))


CurrentUser = Annotated[User, Depends(get_current_user)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
ControlledTester = Annotated[
    TesterContext,
    Depends(
        require_any_role(
            RoleName.INTERNAL_TESTER.value,
            RoleName.PILOT_TESTER.value,
            RoleName.KVK_REVIEWER.value,
        )
    ),
]
