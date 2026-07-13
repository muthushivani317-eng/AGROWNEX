"""Farm Memory exceptions (docs/CODING_STANDARDS.md → Error Handling)."""
from __future__ import annotations

from app.core.exceptions import NotFoundError


class FarmNotOwnedError(NotFoundError):
    # 404 (not 403) so ownership can't be probed by id enumeration.
    error_code = "farm_not_found"
    message = "Farm not found."


class MemoryNotFoundError(NotFoundError):
    error_code = "memory_not_found"
    message = "Memory not found."
