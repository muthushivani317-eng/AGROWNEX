from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.core.logging import get_logger

from .schemas import LIVE_LIFECYCLE_STATUSES, RulePack

logger = get_logger("disease_risk.registry")


class RulePackRegistry:
    def __init__(self, packs: list[RulePack], *, now: datetime | None = None) -> None:
        self.now = now or datetime.now(UTC)
        self.active = [pack for pack in packs if self._executable(pack)]
        self.reason = None if self.active else "DISEASE_RISK_RULE_PACK_UNAVAILABLE"

    def _executable(self, pack: RulePack) -> bool:
        return (
            pack.approval_status in LIVE_LIFECYCLE_STATUSES
            and pack.review_expires_at > self.now
            and pack.content_hash == pack.expected_hash()
        )

    def find(self, *, crop_id: str, region: str | None, season: str | None) -> RulePack | None:
        return next(
            (
                pack
                for pack in self.active
                if pack.crop_id == crop_id
                and (region is None or region in pack.regions)
                and (season is None or season in pack.seasons)
            ),
            None,
        )


# Where real, source-cited disease-risk rule packs live once someone adds them
# (see the README in that directory before adding one -- same safety gate as
# app.modules.calendar.registry's VERIFIED_SCHEDULES_DIR). Every *.json file
# here is loaded at import time; `*.json.example` (the template) is
# intentionally not picked up.
RULE_PACKS_DIR = Path(__file__).resolve().parent / "data" / "rule_packs"


def _load_rule_pack_entries(directory: Path = RULE_PACKS_DIR) -> list[dict[str, Any]]:
    """Read every *.json file in `directory` as a raw rule-pack entry.

    A file that isn't valid JSON is skipped with a warning rather than
    crashing app startup -- a typo in one crop/disease's file must not take
    down disease-risk evaluation for every other crop.
    """
    if not directory.is_dir():
        return []
    entries: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(
                "Skipping unreadable rule pack file",
                extra={"path": str(path), "error": str(exc)},
            )
            continue
        if not isinstance(raw, dict):
            logger.warning(
                "Skipping rule pack file: expected a JSON object",
                extra={"path": str(path)},
            )
            continue
        entries.append(raw)
    return entries


def _parse_rule_pack_entries(raw_entries: list[dict[str, Any]]) -> list[RulePack]:
    """Validate raw entries into RulePack models, skipping invalid ones.

    Schema/hash/lifecycle-status checks happen later, inside
    RulePackRegistry itself (the same logic regardless of where the packs
    came from) -- this step only handles "is this even a well-formed
    RulePack," logging and skipping anything that isn't rather than crashing
    startup on one bad file.
    """
    parsed: list[RulePack] = []
    for raw in raw_entries:
        try:
            parsed.append(RulePack.model_validate(raw))
        except ValidationError as exc:
            logger.warning(
                "Skipping invalid rule pack entry",
                extra={"pack_id": raw.get("pack_id"), "error": str(exc)},
            )
    return parsed


def load_active_registry(*, now: datetime | None = None) -> RulePackRegistry:
    """Build the live registry from every rule pack file on disk."""
    return RulePackRegistry(_parse_rule_pack_entries(_load_rule_pack_entries()), now=now)
