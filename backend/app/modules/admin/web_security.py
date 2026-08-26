"""Browser-session protections for the separately deployed Admin PWA."""

from __future__ import annotations

import hashlib
import hmac
from typing import Protocol


class HeaderRequest(Protocol):
    headers: object


class InvalidCsrfTokenError(Exception):
    pass


class InvalidAdminOriginError(Exception):
    pass


def build_csrf_token(session_cookie: str, secret: str) -> str:
    return hmac.new(secret.encode(), session_cookie.encode(), hashlib.sha256).hexdigest()


def require_csrf_token(provided: str | None, expected: str) -> None:
    if not provided or not hmac.compare_digest(provided, expected):
        raise InvalidCsrfTokenError("ADMIN_CSRF_INVALID")


def require_admin_origin(request: HeaderRequest, allowed_origins: list[str]) -> None:
    origin = request.headers.get("origin")  # type: ignore[attr-defined]
    if not origin or origin not in allowed_origins:
        raise InvalidAdminOriginError("ADMIN_ORIGIN_INVALID")
