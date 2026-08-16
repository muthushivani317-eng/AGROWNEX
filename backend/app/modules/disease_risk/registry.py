from __future__ import annotations

from datetime import UTC, datetime

from .schemas import RulePack


class RulePackRegistry:
    def __init__(self, packs: list[RulePack], *, now: datetime | None = None) -> None:
        self.now = now or datetime.now(UTC)
        self.active = [pack for pack in packs if self._executable(pack)]
        self.reason = None if self.active else "DISEASE_RISK_RULE_PACK_UNAVAILABLE"

    def _executable(self, pack: RulePack) -> bool:
        return (
            pack.approval_status == "VERIFIED"
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
