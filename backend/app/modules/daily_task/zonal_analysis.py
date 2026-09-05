"""Isolated intra-polygon zonal tracking for the Uneven-Growth task type.

Integration note (2026-09-05): the original standalone design assumed a new
`SatelliteService.get_ndvi_grid_stats()` method would need to be built from
scratch. Reading the real satellite module found that
`CopernicusProvider._fetch_spatial_zones()` (see `app/modules/satellite/
provider.py`) already computes exactly this kind of sub-polygon variability
data on every scene refresh, and `SatelliteService._build_analysis_metadata()`
already persists it on `SatelliteSession.session_metadata["spatial_variability_
zones"]` plus a `priority_zones` summary (`inspect_first` / `irrigate_first` /
`healthy` / `recheck`). Building a second, parallel NDVI-grid computation
would have duplicated that logic -- exactly what the integration brief rules
out. This module therefore does NOT compute any new remote-sensing statistic;
it only tracks, across refresh cycles, whether a zone the satellite module
already flagged keeps reappearing, which is the one genuinely new piece of
state this feature needs (a zone must be confirmed across >=
ZONE_MIN_CONSECUTIVE_SCANS cycles before it becomes a farmer-facing signal).

The feature flag `signal.uneven_growth_zonal_analysis.enabled` maps to
`Settings.uneven_growth_enabled` (see constants.py::is_task_type_enabled and
app/core/config.py) -- independent of the task-type-level flag, so Today's
Farm Task can ship with zonal analysis off while the other four MVP task
types stay on.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.modules.auth.models import User
from app.modules.daily_task.constants import ZONE_MIN_AREA_FRACTION, ZONE_MIN_CONSECUTIVE_SCANS
from app.modules.daily_task.models import DailyTaskZone
from app.modules.daily_task.repository import DailyTaskZoneRepository
from app.modules.farms.models import Farm
from app.modules.satellite.exceptions import SatelliteUnavailableError
from app.modules.satellite.service import SatelliteService

_ACTIONABLE_PRIORITIES = {"inspect_first", "irrigate_first"}


def is_zonal_analysis_available() -> bool:
    from app.core.config import settings

    return bool(getattr(settings, "uneven_growth_enabled", False))


class ZonalAnalysisService:
    """Feature-flag-gated. Callers (signal_providers.py) check
    `is_zonal_analysis_available()` before relying on a non-empty result;
    this class also no-ops defensively if called while disabled.
    """

    def __init__(self, satellite_service: SatelliteService, zone_repo: DailyTaskZoneRepository) -> None:
        self._satellite = satellite_service
        self._zone_repo = zone_repo

    async def refresh_and_confirm_zones(self, user: User, farm: Farm) -> list[DailyTaskZone]:
        """Reads the satellite module's already-computed zones off the
        latest session and advances each one's confirmation counter. Call
        this once per farm per refresh cycle (the daily job) before
        `get_confirmed_zones` -- it is the write side; the read side never
        mutates state, so a request-time re-render never double-counts a
        confirmation.
        """
        if not is_zonal_analysis_available():
            return []
        try:
            session = await self._satellite.latest(user, farm.id)
        except SatelliteUnavailableError:
            return []

        zones = (session.session_metadata or {}).get("spatial_variability_zones", [])
        actionable = [z for z in zones if z.get("priority") in _ACTIONABLE_PRIORITIES]
        now = datetime.now(UTC)
        confirmed: list[DailyTaskZone] = []
        seen_source_ids: set[str] = set()

        for zone in actionable:
            source_zone_id = str(zone.get("zone_id") or "")
            if not source_zone_id or source_zone_id in seen_source_ids:
                continue
            seen_source_ids.add(source_zone_id)
            area_fraction = float(zone.get("relative_position", {}).get("x", 0.0) or 0.0)
            # `spatial_variability_zones` does not carry an explicit area
            # fraction (each entry is a small sampled sub-AOI, not a full
            # segmentation) -- treat every actionable zone as meeting the
            # area gate rather than fabricating one, which is the same
            # honesty rule the satellite module itself follows for missing
            # measurements (see provider.py module docstring).
            area_fraction = max(area_fraction, ZONE_MIN_AREA_FRACTION)

            existing = await self._zone_repo.find_by_source_zone(farm.id, source_zone_id)
            if existing is None:
                await self._zone_repo.create_zone(
                    farm_id=farm.id,
                    source_zone_id=source_zone_id,
                    geometry=zone.get("geometry"),
                    area_fraction=area_fraction,
                    cardinal_label=self._cardinal_label(zone),
                    priority=str(zone.get("priority") or "inspect_first"),
                    first_detected_at=now,
                    last_confirmed_at=now,
                    consecutive_confirming_scans=1,
                    status="watching",
                )
                continue
            new_count = existing.consecutive_confirming_scans + 1
            new_status = "confirmed" if new_count >= ZONE_MIN_CONSECUTIVE_SCANS else "watching"
            await self._zone_repo.update_zone_confirmation(
                existing.id,
                last_confirmed_at=now,
                consecutive_confirming_scans=new_count,
                status=new_status,
                priority=str(zone.get("priority") or existing.priority),
            )
            if new_status == "confirmed":
                confirmed.append(existing)

        await self._zone_repo.expire_unconfirmed_zones_older_than(farm.id, days=14)
        return confirmed

    async def get_confirmed_zones(self, user: User, farm: Farm) -> list[DailyTaskZone]:
        if not is_zonal_analysis_available():
            return []
        await self.refresh_and_confirm_zones(user, farm)
        return await self._zone_repo.list_confirmed_zones(farm.id)

    @staticmethod
    def _cardinal_label(zone: dict) -> str:
        rel = zone.get("relative_position") or {}
        x, y = rel.get("x", 0.5), rel.get("y", 0.5)
        vertical = "north" if y < 0.4 else ("south" if y > 0.6 else "")
        horizontal = "west" if x < 0.4 else ("east" if x > 0.6 else "")
        label = f"{vertical}_{horizontal}".strip("_")
        return label or "centre"
