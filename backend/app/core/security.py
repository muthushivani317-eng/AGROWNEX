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


def verify_id_token(token: str) -> dict[str, Any]:
    """Verify a Firebase ID token and return its decoded claims.

    Raises UnauthorizedError for missing config or invalid/expired tokens.
    """
    app = _get_firebase_app()
    if app is None:
        raise UnauthorizedError("Authentication is not configured on the server.")

    try:
        from firebase_admin import auth as firebase_auth

        claims = firebase_auth.verify_id_token(
            token,
            app=app,
            check_revoked=True,
            clock_skew_seconds=30,
        )
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
