"""Normalized boundary for trusted server-side action producers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SourceAction:
    source_feature: str
    source_record_id: str
    source_version: str
    action_code: str
    suggestion_time: datetime
    source_verified: bool
    crop_cycle_id: str | None = None
    due_at: datetime | None = None
    expires_at: datetime | None = None

    @property
    def actionable(self) -> bool:
        return bool(
            self.source_feature.strip()
            and self.source_record_id.strip()
            and self.action_code.strip()
        )
