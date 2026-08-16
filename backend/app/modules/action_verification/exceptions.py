"""Action Verification exceptions (docs/CODING_STANDARDS.md → Error Handling).

Ownership violations use NotFoundError (404), not ForbiddenError (403) --
matching the convention used across the rest of the app: an action/farm the
farmer doesn't own must look identical to one that doesn't exist at all, so
ownership can't be probed by id. Previously this module raised a plain
PermissionError for that case, which isn't an AppError subclass, so it fell
through to the generic unhandled-exception handler and returned a raw HTTP
500 -- breaking the convention and polluting error monitoring with noise on
every occurrence (found in the 2026-08 pre-release audit).
"""
from __future__ import annotations

from app.core.exceptions import NotFoundError


class ActionNotFoundError(NotFoundError):
    error_code = "action_not_found"
    message = "Action not found."
