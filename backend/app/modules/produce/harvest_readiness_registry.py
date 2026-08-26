from __future__ import annotations

from app.modules.produce.harvest_readiness import ReadinessCriteria


class HarvestReadinessRegistry:
    """Server-owned verified readiness criteria. Empty is a supported safe state."""

    def __init__(self, entries: list[ReadinessCriteria] | None = None) -> None:
        self._active = {
            entry.crop.strip().lower(): entry for entry in entries or [] if entry.active_verified
        }

    def resolve(self, crop: str | None) -> ReadinessCriteria | None:
        return self._active.get(crop.strip().lower()) if crop else None

    @property
    def active_count(self) -> int:
        return len(self._active)


# No repository criteria pack currently carries documented expert approval.
ACTIVE_HARVEST_READINESS_REGISTRY = HarvestReadinessRegistry()
