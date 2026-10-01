"""Admin dependency injection (docs/BACKEND_ARCHITECTURE.md → DI).

Wires request → repository → service and resolves the authenticated **admin**
context (RBAC + status check) from the current user. The client IP is captured for
the immutable audit trail (docs/SECURITY.md). No global singletons.
"""

from __future__ import annotations

import hashlib
import time
from typing import Annotated

from fastapi import Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import build_cache
from app.core.config import settings
from app.core.database import get_session
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import verify_id_token, verify_session_cookie
from app.modules.admin.service import AdminContext, AdminService
from app.modules.admin.web_security import (
    InvalidAdminOriginError,
    InvalidCsrfTokenError,
    build_csrf_token,
    require_admin_origin,
    require_csrf_token,
)
from app.modules.auth.constants import UserStatus
from app.modules.auth.dependencies import AuthServiceDep, CurrentUser

__all__ = ["AdminContextDep", "AdminServiceDep", "CurrentUser", "require_admin_mfa"]


def get_admin_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdminService:
    return AdminService(session)


AdminServiceDep = Annotated[AdminService, Depends(get_admin_service)]


def require_admin_mfa(claims: dict) -> None:
    """Reject admin access unless the Firebase sign-in used a second factor.

    403, not 401: the farmer's own sign-in is valid, so the app must not
    treat this as "session expired" and sign the farmer out.
    """
    if settings.admin_require_mfa and not (claims.get("firebase") or {}).get(
        "sign_in_second_factor"
    ):
        raise ForbiddenError(
            "Multi-factor authentication is required for Admin access.",
            error_code="admin_mfa_required",
        )


# Admin browser sessions ended with "Sign out". Keyed by a hash of the cookie,
# kept for the longest possible cookie life. Only that browser session ends;
# the person's other devices (e.g. the farmer app) stay signed in.
_revoked_admin_sessions = build_cache(
    namespace="admin-revoked-sessions", ttl_seconds=336 * 60 * 60
)


def _session_fingerprint(cookie: str) -> str:
    return hashlib.sha256(cookie.encode()).hexdigest()


def revoke_admin_session(cookie: str) -> None:
    _revoked_admin_sessions.set(_session_fingerprint(cookie), True)


def is_admin_session_revoked(cookie: str) -> bool:
    return bool(_revoked_admin_sessions.get(_session_fingerprint(cookie)))


def _client_ip(request: Request) -> str | None:
    # Only honour the proxy header when a trusted edge proxy is known to
    # sanitize it (settings.trust_proxy_headers) -- otherwise the audit trail
    # could be forged by a client-supplied header. Falls back to the direct
    # TCP peer (docs/DEPLOYMENT.md, docs/SECURITY.md).
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


async def get_admin_context(
    request: Request,
    response: Response,
    service: AdminServiceDep,
    auth_service: AuthServiceDep,
) -> AdminContext:
    """Resolve Bearer or HttpOnly web-session auth, then enforce active AdminUser.

    Browser cookie mutations additionally require exact-origin and CSRF checks.
    Native/mobile callers retain the existing Bearer-token contract.
    """
    authorization = request.headers.get("authorization", "")
    cookie = request.cookies.get(settings.admin_session_cookie_name)
    bearer = authorization.startswith("Bearer ")
    if bearer:
        claims = verify_id_token(authorization[7:], strict_revocation=True)
    elif cookie:
        if is_admin_session_revoked(cookie):
            raise UnauthorizedError(
                "Admin session has ended. Please sign in again.",
                error_code="authentication_invalid",
            )
        claims = verify_session_cookie(cookie)
        csrf = build_csrf_token(cookie, settings.session_secret)
        response.headers["X-CSRF-Token"] = csrf
        response.headers["Cache-Control"] = "private, no-store"
        # Reads too: a cookie request coming from any other site (even one
        # listed in CORS_ORIGINS) must not be able to read admin data.
        if request.headers.get("origin") and request.headers.get("origin") not in settings.admin_web_origins:
            raise ForbiddenError(
                "The admin request origin is not allowed.",
                error_code="admin_origin_invalid",
            )
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            if not request.url.path.endswith("/admin/web-session"):
                auth_time = claims.get("auth_time")
                if not isinstance(auth_time, int | float) or (
                    time.time() - auth_time > settings.admin_sensitive_reauth_minutes * 60
                ):
                    raise ForbiddenError(
                        "Recent authentication is required for this Admin action.",
                        error_code="admin_recent_auth_required",
                    )
            try:
                require_admin_origin(request, settings.admin_web_origins)
                require_csrf_token(request.headers.get("x-csrf-token"), csrf)
            except InvalidAdminOriginError as exc:
                raise ForbiddenError(
                    "The admin request origin is not allowed.",
                    error_code="admin_origin_invalid",
                ) from exc
            except InvalidCsrfTokenError as exc:
                raise ForbiddenError(
                    "The admin security token is invalid.",
                    error_code="admin_csrf_invalid",
                ) from exc
    else:
        raise UnauthorizedError(
            "Admin authentication is required.",
            error_code="authentication_required",
        )
    current_user = await auth_service.get_user_by_firebase_uid(claims["uid"])
    if current_user.status != UserStatus.ACTIVE or current_user.deleted_at is not None:
        raise UnauthorizedError(
            "Authentication is no longer active.",
            error_code="authentication_invalid",
        )
    context = await service.resolve_admin(current_user, ip_address=_client_ip(request))
    if bearer:
        # Same MFA bar as the web session (whose cookie is only minted after
        # MFA): a phone-OTP-only token, e.g. after a SIM swap, must never reach
        # admin data. Checked after resolve_admin so non-admins still get the
        # usual "not an admin" answer.
        require_admin_mfa(claims)
    return context


AdminContextDep = Annotated[AdminContext, Depends(get_admin_context)]
