"""Firebase JWT verification (docs/SECURITY.md → Authentication / JWT).

Every protected API requires a valid Firebase ID token. Tokens are verified by
the Firebase Admin SDK; we never store passwords. The Admin app is initialised
lazily so the service boots (and health-checks pass) even before credentials are
provisioned.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.core.logging import get_logger

logger = get_logger("security")


@lru_cache
def _get_firebase_app() -> Any | None:
    """Initialise (once) and return the Firebase Admin app, or None if unconfigured."""
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

        return firebase_auth.verify_id_token(token, app=app)
    except Exception as exc:  # noqa: BLE001
        # Do not log the token itself (docs/SECURITY.md → Logging).
        logger.info("Token verification failed: %s", type(exc).__name__)
        raise UnauthorizedError("Invalid or expired authentication token.") from exc
