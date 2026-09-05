"""Domain exceptions for the daily_task module, following the app-wide
`AppError` hierarchy (`app/core/exceptions.py`) so the global error handlers
translate them into the standard envelope automatically -- no local
HTTPException handling needed in router.py.
"""
from __future__ import annotations

from app.core.exceptions import ConflictError, NotFoundError


class TaskNotFoundError(NotFoundError):
    error_code = "daily_task_not_found"
    message = "Task not found."


class TaskAlreadyClosedError(ConflictError):
    error_code = "daily_task_already_closed"
    message = "This task has already been responded to."


class EvidencePackNotFoundError(NotFoundError):
    error_code = "evidence_pack_not_found"
    message = "Evidence pack not found."
