"""Notification-specific exceptions (docs/CODING_STANDARDS.md → Error Handling)."""
from __future__ import annotations

from app.core.exceptions import NotFoundError


class NotificationNotFoundError(NotFoundError):
    error_code = "notification_not_found"
    message = "Notification not found."
