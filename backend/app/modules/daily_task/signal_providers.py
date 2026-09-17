"""Layer 1 -- Signal Providers.

Every provider is an ADAPTER, not a reimplementation: each one calls into an
existing module's already-computed result (SatelliteService, WeatherService,
CalendarService) and translates it into an `EvidenceSignal` (Layer 2). None
of these classes touch Copernicus, Open-Meteo, or any other external API
directly, and none re-derive an index the satellite module already computed.

Each provider exposes one method:
    async def collect(self, user: User, farm: Farm) -> list[EvidenceSignal]
`service.py` runs all providers for a farm uniformly and hands the combined
candidate list to the ranking engine (Layer 3). `user` is threaded through
explicitly because every real service method on this app takes
`(user, farm_id)`, not a bare `farm_id` (see `app/modules/satellite/service.py`,
`app/modules/weather/service.py`).
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Protocol

from app.modules.auth.models import User
from app.modules.calendar.service import CalendarService
from app.modules.daily_task.constants import (
    DRAINAGE_HEAVY_RAIN_MM_24H,
    IRRIGATION_SUPPRESS_IF_RAIN_FORECAST_MM,
    IRRIGATION_SUPPRESS_IF_RAIN_WITHIN_MM,
    SIGNAL_VALIDITY_HOURS,
    SOWING_EXPECTED_EMERGENCE_DAYS_DEFAULT,
    SOWING_GRACE_PERIOD_DAYS,
    Confidence,
    Severity,
    SignalType,
    SourceModule,
    TaskType,
    Urgency,
)
from app.modules.daily_task.schemas import EvidenceSignal
from app.modules.daily_task.zonal_analysis import ZonalAnalysisService, is_zonal_analysis_available
from app.modules.farms.models import Farm
from app.modules.satellite.constants import NDVI_LOW
from app.modules.satellite.exceptions import SatelliteUnavailableError
from app.modules.satellite.service import SatelliteService
from app.modules.weather.service import WeatherService

_DRY_MOISTURE_STATUSES = {"dry", "very_dry"}
_HIGH_STRESS_LEVELS = {"moderate", "severe"}
_WATERLOGGING_ACTIONABLE_DECISIONS = {
    "observed_surface_water",
    "possible_waterlogging",
    "possible_flood_risk",
    "rainfall_risk_only",
    "review_required",
}
_WATERLOGGING_CAUTIOUS_DECISIONS = {"rainfall_risk_only", "review_required"}
_WATERLOGGING_HIGHER_CONFIDENCE_DECISIONS = {
    "observed_surface_water",
    "possible_waterlogging",
    "possible_flood_risk",
}


def _dedupe_key(farm_id, signal_type: SignalType, bucket: str) -> str:
    raw = f"{farm_id}:{signal_type.value}:{bucket}"
    return hashlib.sha256(raw.encode()).hexdigest()[:40]


def _valid_until(signal_type: SignalType, now: datetime) -> datetime:
    return now + timedelta(hours=SIGNAL_VALIDITY_HOURS.get(signal_type, 48))


def _sum_recent_daily_rain_mm(bundle, *, days: int, now: datetime) -> float:
    """Sums `WeatherBundle.daily[].precipitation_sum_mm` for the last N
    calendar days up to and including today. Open-Meteo's daily block
    (as configured by `WeatherService`) includes recent past days when
    `past_days` is requested; a day missing from the payload simply
    contributes 0 rather than raising -- this provider must never invent
    a rainfall figure that wasn't actually returned.
    """
    if not bundle or not bundle.daily:
        return 0.0
    cutoff = (now.date() - timedelta(days=days)).isoformat()
    total = 0.0
    for point in bundle.daily:
        if point.date >= cutoff and point.date <= now.date().isoformat() and point.precipitation_sum_mm:
            total += float(point.precipitation_sum_mm)
    return total


def _sum_recent_hourly_rain_mm(bundle, *, hours: int, now: datetime) -> float:
    """Sums `WeatherBundle.hourly[].precipitation_mm` for the last N hours --
    used for the drainage trigger, which needs a same-day 24h figure rather
    than the coarser daily total.
    """
    if not bundle or not bundle.hourly:
        return 0.0
    cutoff = now - timedelta(hours=hours)
    total = 0.0
    for point in bundle.hourly:
        try:
            point_time = datetime.fromisoformat(point.time)
        except ValueError:
            continue
        if point_time.tzinfo is None:
            point_time = point_time.replace(tzinfo=UTC)
        if point_time <= now and point_time >= cutoff and point.precipitation_mm:
            total += float(point.precipitation_mm)
    return total


def _forecast_rain_within_48h_mm(bundle, *, now: datetime) -> float:
    if not bundle or not bundle.daily:
        return 0.0
    upper = (now.date() + timedelta(days=2)).isoformat()
    total = 0.0
    for point in bundle.daily:
        if point.date >= now.date().isoformat() and point.date <= upper and point.precipitation_sum_mm:
            total += float(point.precipitation_sum_mm)
    return total


class SignalProvider(Protocol):
    async def collect(self, user: User, farm: Farm) -> list[EvidenceSignal]: ...


class IrrigationDrynessProvider:
    """Reuses `SatelliteService.latest()`'s already-computed `moisture_status`
    / `stress_level` classification (see `app/modules/satellite/engine.py::
    classify_moisture`) and `WeatherService.get_by_farm()`'s rainfall data --
    no new remote-sensing or forecast computation.
    """

    def __init__(self, satellite_service: SatelliteService, weather_service: WeatherService) -> None:
        self._satellite = satellite_service
        self._weather = weather_service

    async def collect(self, user: User, farm: Farm) -> list[EvidenceSignal]:
        try:
            session = await self._satellite.latest(user, farm.id)
        except SatelliteUnavailableError:
            return []  # gate: no usable scene yet -> insufficient data, never a guess

        if session.moisture_status not in _DRY_MOISTURE_STATUSES:
            return []

        bundle = await self._weather.get_by_farm(user, farm.id)
        now = datetime.now(UTC)
        recent_rain = _sum_recent_daily_rain_mm(bundle, days=3, now=now)
        if recent_rain >= IRRIGATION_SUPPRESS_IF_RAIN_WITHIN_MM:
            return []  # recent rain already addresses the dryness
        if _forecast_rain_within_48h_mm(bundle, now=now) >= IRRIGATION_SUPPRESS_IF_RAIN_FORECAST_MM:
            return []  # imminent rain -- do not ask the farmer to irrigate right before it rains

        confidence = (
            Confidence.HIGH if session.stress_level in _HIGH_STRESS_LEVELS else Confidence.MEDIUM
        )
        signal = EvidenceSignal(
            farmer_id=farm.user_id,
            field_id=farm.id,
            signal_type=SignalType.IRRIGATION_DRYNESS,
            source_module=SourceModule.SATELLITE,
            observed_at=datetime.combine(session.capture_date, datetime.min.time(), tzinfo=UTC)
            if session.capture_date
            else now,
            valid_until=_valid_until(SignalType.IRRIGATION_DRYNESS, now),
            confidence=confidence,
            severity=Severity.ATTENTION,
            urgency=Urgency.WITHIN_48H,
            evidence_summary={"moisture_status": session.moisture_status, "trend": session.trend},
            evidence_technical={
                "ndmi": session.ndmi,
                "ndvi": session.ndvi,
                "confidence_pct": session.confidence,
                "capture_date": session.capture_date.isoformat() if session.capture_date else None,
                "recent_rain_mm_3d": recent_rain,
            },
            evidence_refs={"satellite_session_id": str(session.id)},
            recommended_task_type=TaskType.IRRIGATION_INSPECTION,
            dedupe_key=_dedupe_key(
                farm.id, SignalType.IRRIGATION_DRYNESS, str(session.capture_date or now.date())
            ),
        )
        return [signal]


class UnevenGrowthZoneProvider:
    """Delegates entirely to `ZonalAnalysisService`, which itself reuses the
    satellite module's own `spatial_variability_zones` (computed by
    `CopernicusProvider._fetch_spatial_zones` and persisted on
    `SatelliteSession.session_metadata`) rather than computing any new
    sub-polygon statistics -- see zonal_analysis.py for why no new
    "NDVI grid" computation was needed here.
    """

    def __init__(self, zonal_service: ZonalAnalysisService) -> None:
        self._zonal = zonal_service

    async def collect(self, user: User, farm: Farm) -> list[EvidenceSignal]:
        if not is_zonal_analysis_available():
            return []

        confirmed_zones = await self._zonal.get_confirmed_zones(user, farm)
        signals: list[EvidenceSignal] = []
        now = datetime.now(UTC)
        for zone in confirmed_zones:
            signals.append(
                EvidenceSignal(
                    farmer_id=farm.user_id,
                    field_id=farm.id,
                    signal_type=SignalType.UNEVEN_GROWTH_ZONE,
                    source_module=SourceModule.SATELLITE,
                    observed_at=zone.last_confirmed_at,
                    valid_until=_valid_until(SignalType.UNEVEN_GROWTH_ZONE, now),
                    confidence=Confidence.HIGH
                    if zone.consecutive_confirming_scans >= 3
                    else Confidence.MEDIUM,
                    severity=Severity.ATTENTION,
                    urgency=Urgency.THIS_WEEK,
                    evidence_summary={
                        "zone_label": zone.cardinal_label,
                        "area_fraction": zone.area_fraction,
                    },
                    evidence_technical={
                        "zone_id": str(zone.id),
                        "source_zone_id": zone.source_zone_id,
                        "consecutive_scans": zone.consecutive_confirming_scans,
                        "priority": zone.priority,
                    },
                    evidence_refs={"daily_task_zone_id": str(zone.id)},
                    recommended_task_type=TaskType.UNEVEN_GROWTH_INSPECTION,
                    dedupe_key=_dedupe_key(farm.id, SignalType.UNEVEN_GROWTH_ZONE, zone.source_zone_id),
                )
            )
        return signals


class DrainageRiskProvider:
    """Reuses the EXISTING, already policy-gated waterlogging assessment via
    `SatelliteService.latest_waterlogging()` (which itself builds evidence
    and calls the pure, policy-gated `satellite.waterlogging.assess_
    waterlogging()`). This provider adds no water-detection logic of its own
    and never loosens that gate -- a `REVIEW_REQUIRED` / `RAINFALL_RISK_ONLY`
    decision is surfaced as a cautious "inspect" prompt only, tagged with a
    policy flag the ranking engine can act on, never as a flood claim.
    """

    def __init__(self, satellite_service: SatelliteService, weather_service: WeatherService) -> None:
        self._satellite = satellite_service
        self._weather = weather_service

    async def collect(self, user: User, farm: Farm) -> list[EvidenceSignal]:
        bundle = await self._weather.get_by_farm(user, farm.id)
        now = datetime.now(UTC)
        recent_rain = _sum_recent_hourly_rain_mm(bundle, hours=24, now=now)
        if recent_rain < DRAINAGE_HEAVY_RAIN_MM_24H:
            return []

        assessment = await self._satellite.latest_waterlogging(user, farm.id)
        if assessment is None or assessment.decision == "insufficient_data":
            return []  # gate: absence of evidence never becomes a signal
        if assessment.decision == "clear":
            return []
        if assessment.decision not in _WATERLOGGING_ACTIONABLE_DECISIONS:
            return []

        policy_flags = (
            ["waterlogging_policy_gated"]
            if assessment.decision in _WATERLOGGING_CAUTIOUS_DECISIONS
            else []
        )
        confidence = (
            Confidence.MEDIUM
            if assessment.decision in _WATERLOGGING_HIGHER_CONFIDENCE_DECISIONS
            else Confidence.LOW
        )

        signal = EvidenceSignal(
            farmer_id=farm.user_id,
            field_id=farm.id,
            signal_type=SignalType.DRAINAGE_RISK,
            source_module=SourceModule.SATELLITE,
            observed_at=assessment.observed_at or now,
            valid_until=_valid_until(SignalType.DRAINAGE_RISK, now),
            confidence=confidence,
            severity=Severity.URGENT,
            urgency=Urgency.TODAY,
            evidence_summary={"rain_mm_24h": round(recent_rain, 1), "surface_change": assessment.decision},
            evidence_technical={
                "explanation": assessment.explanation,
                "freshness": assessment.freshness,
                "coverage_pct": assessment.coverage_pct,
                "source": assessment.source,
            },
            evidence_refs={"waterlogging_assessment_id": str(assessment.id)},
            policy_flags=policy_flags,
            recommended_task_type=TaskType.DRAINAGE_INSPECTION,
            dedupe_key=_dedupe_key(farm.id, SignalType.DRAINAGE_RISK, now.strftime("%Y-%m-%d")),
        )
        return [signal]


class SowingGerminationProvider:
    """Reuses `CalendarService` for an expected-emergence event when the crop
    calendar has generated one, and `SatelliteService.latest()` for whether
    green-up has started -- via the same `ndvi` field and `NDVI_LOW`
    threshold the satellite dashboard already uses (`app/modules/satellite/
    constants.py`), not a new threshold invented here.
    """

    def __init__(self, calendar_service: CalendarService, satellite_service: SatelliteService) -> None:
        self._calendar = calendar_service
        self._satellite = satellite_service

    async def collect(self, user: User, farm: Farm) -> list[EvidenceSignal]:
        if not farm.sowing_date or not farm.crop:
            return []

        expected_days = SOWING_EXPECTED_EMERGENCE_DAYS_DEFAULT
        try:
            events = await self._calendar.for_farm(user, farm.id, page=1, page_size=100)
            emergence_events = [e for e in events if getattr(e, "growth_stage", None) == "emergence"]
            if emergence_events:
                latest_emergence = max(e.scheduled_date for e in emergence_events)
                expected_days = max((latest_emergence - farm.sowing_date).days, 1)
        except Exception:  # noqa: BLE001 -- calendar lookup is best-effort context, never blocking
            pass

        grace_deadline = farm.sowing_date + timedelta(days=expected_days + SOWING_GRACE_PERIOD_DAYS)
        now = datetime.now(UTC)
        if now.date() < grace_deadline:
            return []

        try:
            session = await self._satellite.latest(user, farm.id)
        except SatelliteUnavailableError:
            return []  # gate: no usable scene through the window -> insufficient data, not a finding

        if session.capture_date is None or session.capture_date < farm.sowing_date:
            return []  # no scene actually covering the post-sowing period yet
        if session.ndvi is not None and session.ndvi >= NDVI_LOW:
            return []  # green-up looks normal

        signal = EvidenceSignal(
            farmer_id=farm.user_id,
            field_id=farm.id,
            signal_type=SignalType.SOWING_GERMINATION_DELAY,
            source_module=SourceModule.CALENDAR,
            observed_at=now,
            valid_until=_valid_until(SignalType.SOWING_GERMINATION_DELAY, now),
            confidence=Confidence.MEDIUM,
            severity=Severity.ATTENTION,
            urgency=Urgency.TODAY,
            evidence_summary={"days_past_expected_emergence": (now.date() - grace_deadline).days},
            evidence_technical={
                "sowing_date": farm.sowing_date.isoformat(),
                "crop": farm.crop,
                "ndvi": session.ndvi,
                "expected_emergence_days": expected_days,
            },
            evidence_refs={"satellite_session_id": str(session.id)},
            recommended_task_type=TaskType.SOWING_GERMINATION_CHECK,
            dedupe_key=_dedupe_key(farm.id, SignalType.SOWING_GERMINATION_DELAY, farm.sowing_date.isoformat()),
        )
        return [signal]


class SoilNutrientEvidenceHook:
    """Not a standalone trigger at MVP -- Soil Scan / Nutrient Analysis
    findings are read-only corroborating context another provider MAY cite
    in `evidence_refs`, never their own daily task (matches the unified
    implementation brief's explicit MVP scope of exactly 5 task types).
    """

    def __init__(self, nutrient_service, soil_service) -> None:
        self._nutrient = nutrient_service
        self._soil = soil_service


class DiseasePhotoHook:
    """Same pattern as SoilNutrientEvidenceHook -- read-only context, never a
    trigger this layer owns. Disease Detection's own guardrails (never a
    satellite-only diagnosis) stay fully intact and un-duplicated.
    """

    def __init__(self, disease_service) -> None:
        self._disease = disease_service
