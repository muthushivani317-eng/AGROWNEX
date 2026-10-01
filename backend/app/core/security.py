"""Firebase JWT verification (docs/SECURITY.md → Authentication / JWT).

Every protected API requires a valid Firebase ID token. Tokens are verified by
the Firebase Admin SDK; we never store passwords. The Admin app is initialised
lazily so the service boots (and health-checks pass) even before credentials are
provisioned.
"""
from __future__ import annotations

import json
import os
import time
from functools import lru_cache
from typing import Any

from app.core.cache import build_cache
from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.core.logging import get_logger

logger = get_logger("security")


@lru_cache
def _get_firebase_app() -> Any | None:
    """Initialise (once) and return the Firebase Admin app, or None if unconfigured."""
    emulator_host = settings.firebase_auth_emulator_host.strip()
    if emulator_host:
        if settings.is_production:
            logger.error("Firebase Auth Emulator refused in production.")
            return None
        if not settings.firebase_project_id.startswith("demo-"):
            logger.error("Firebase emulator requires a demo-* project id.")
            return None
        os.environ["FIREBASE_AUTH_EMULATOR_HOST"] = emulator_host
        try:
            import firebase_admin

            return firebase_admin.initialize_app(
                options={"projectId": settings.firebase_project_id}
            )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to initialise Firebase Auth Emulator client.")
            return None
    if not settings.firebase_project_id or not settings.firebase_credentials_json:
        logger.warning("Firebase not configured — token verification disabled.")
        return None
    try:
        import firebase_admin
        from firebase_admin import credentials

        cred = credentials.Certificate(json.loads(settings.firebase_credentials_json))
        return firebase_admin.initialize_app(cred)
    except Exception:  # noqa: BLE001 — startup diagnostics only
        logger.exception("Failed to initialise Firebase Admin SDK.")
        return None


def ensure_firebase_app() -> Any | None:
    """Public accessor: initialise (once) and return the Admin app, or None.

    Used by push delivery (FCM) to guarantee the default Admin app exists before
    calling ``firebase_admin.messaging`` — and to degrade honestly when Firebase
    is not configured instead of pretending a push was sent.
    """
    return _get_firebase_app()


# Revocation/disabled state per Firebase user, cached briefly. Signature,
# issuer, audience and expiry are still verified locally on EVERY request; only
# the network lookup of "was this user revoked/disabled?" is cached, so a
# revoked farmer loses access within REVOCATION_CACHE_SECONDS. Admin and login
# paths pass strict_revocation=True and always check live.
REVOCATION_CACHE_SECONDS = 60
_revocation_cache = build_cache(namespace="firebase-revocation", ttl_seconds=REVOCATION_CACHE_SECONDS)


def _ensure_not_revoked(claims: dict[str, Any], app: Any, *, strict: bool) -> None:
    from firebase_admin import auth as firebase_auth

    uid = claims.get("uid") or claims.get("sub")
    state = None if strict else _revocation_cache.get(uid)
    if state is None:
        try:
            user = firebase_auth.get_user(uid, app=app)
        except Exception as exc:  # noqa: BLE001
            # The token's signature/expiry are already verified. If only the
            # revocation lookup is unreachable (Google outage, network blip),
            # don't sign out every farmer: allow, uncached, and log. Admin and
            # login paths (strict) still fail closed.
            if strict or isinstance(exc, getattr(firebase_auth, "UserNotFoundError", ())):
                raise
            logger.warning("Revocation lookup unavailable (%s); allowing verified token", type(exc).__name__)
            return
        state = {
            "disabled": bool(user.disabled),
            "valid_after_ms": user.tokens_valid_after_timestamp or 0,
        }
        _revocation_cache.set(uid, state)
    if state["disabled"]:
        raise firebase_auth.UserDisabledError("The user record is disabled.")
    issued_at = claims.get("iat")
    if not isinstance(issued_at, int | float) or issued_at * 1000 < state["valid_after_ms"]:
        raise firebase_auth.RevokedIdTokenError("The Firebase ID token has been revoked.")


def verify_id_token(token: str, *, strict_revocation: bool = False) -> dict[str, Any]:
    """Verify a Firebase ID token and return its decoded claims.

    Raises UnauthorizedError for missing config or invalid/expired/revoked tokens.
    """
    app = _get_firebase_app()
    if app is None:
        raise UnauthorizedError("Authentication is not configured on the server.")

    try:
        from firebase_admin import auth as firebase_auth

        claims = firebase_auth.verify_id_token(
            token,
            app=app,
            check_revoked=False,  # done below, with a short cache
            clock_skew_seconds=30,
        )
        _ensure_not_revoked(claims, app, strict=strict_revocation)
        # The Firebase emulator deliberately relaxes cryptographic token handling.
        # Retain production-equivalent expiry enforcement in non-production E2E
        # validation so an emulator-only token mutation cannot appear valid.
        if settings.firebase_auth_emulator_host:
            expires_at = claims.get("exp")
            if not isinstance(expires_at, int | float) or expires_at < time.time() - 30:
                raise firebase_auth.ExpiredIdTokenError(
                    "Firebase emulator ID token has expired.",
                    None,
                )
        return claims
    except Exception as exc:  # noqa: BLE001
        from firebase_admin import auth as firebase_auth

        # Firebase performs signature, issuer, audience, expiry, not-before and
        # revocation validation. Preserve only a stable safe category.
        if isinstance(exc, firebase_auth.ExpiredIdTokenError):
            code = "AUTHENTICATION_EXPIRED"
            message = "Authentication token has expired."
        elif isinstance(
            exc,
            firebase_auth.RevokedIdTokenError
            | firebase_auth.UserDisabledError,
        ):
            code = "TESTER_ACCESS_REVOKED"
            message = "Authentication is no longer active."
        else:
            code = "AUTHENTICATION_INVALID"
            message = "Invalid authentication token."
        logger.info("Token verification failed: %s", type(exc).__name__)
        raise UnauthorizedError(message, error_code=code) from exc


def create_session_cookie(id_token: str, *, expires_in_seconds: int) -> str:
    """Exchange a verified Firebase ID token for a revocable browser session."""
    app = _get_firebase_app()
    if app is None:
        raise UnauthorizedError("Authentication is not configured on the server.")
    try:
        from firebase_admin import auth as firebase_auth

        return firebase_auth.create_session_cookie(
            id_token,
            expires_in=expires_in_seconds,
            app=app,
        )
    except Exception as exc:  # noqa: BLE001
        logger.info("Session-cookie creation failed: %s", type(exc).__name__)
        raise UnauthorizedError(
            "Secure admin session could not be created.",
            error_code="AUTHENTICATION_INVALID",
        ) from exc


def verify_session_cookie(cookie: str) -> dict[str, Any]:
    """Verify a Firebase browser session including server-side revocation."""
    app = _get_firebase_app()
    if app is None:
        raise UnauthorizedError("Authentication is not configured on the server.")
    try:
        from firebase_admin import auth as firebase_auth

        return firebase_auth.verify_session_cookie(cookie, check_revoked=True, app=app)
    except Exception as exc:  # noqa: BLE001
        logger.info("Admin session verification failed: %s", type(exc).__name__)
        raise UnauthorizedError(
            "Admin session is invalid or expired.",
            error_code="AUTHENTICATION_INVALID",
        ) from exc
