"""Satellite Alert Engine (docs: ALERT ENGINE — deterministic, no fabrication).

Pure functions that turn a session's assessment into localized alerts. Codes are
``satellite.alert.<key>`` so the Tamil-first client renders the wording. Integrated
with the Notification Engine via a collector (see the notifications module). No I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.satellite.constants import (
    CLOUD_ADVISORY,
    NDMI_MOISTURE_STRESS,
    NDVI_DELTA_ABNORMAL,
    NDVI_DELTA_DECLINING,
    NDVI_DELTA_RAPID_DROP,
    NDVI_LOW,
    NDVI_LOW_VIGOR,
    NDVI_VARIATION_STD,
    SEVERITY_ORDER,
    AlertCategory,
    HealthTrend,
    Priority,
    SessionStatus,
    Severity,
    UnavailableReason,
)

_C = AlertCategory
_S = Severity


@dataclass(frozen=True)
class AlertContext:
    """The pure inputs the alert engine reasons about."""

    status: str
    unavailable_reason: str = UnavailableReason.NONE.value
    cloud_cover: float | None = None
    ndvi: float | None = None
    ndmi: float | None = None
    ndvi_delta: float | None = None
    trend: str = HealthTrend.UNKNOWN.value
    ndvi_std: float | None = None


@dataclass(frozen=True)
class AlertDraft:
    code: str
    category: str
    severity: str
    priority: str
    value: float | None = None
    params: dict = field(default_factory=dict)


def _priority_for(severity: str) -> str:
    if severity == _S.CRITICAL.value:
        return Priority.HIGH.value
    if severity == _S.WARNING.value:
        return Priority.MEDIUM.value
    return Priority.LOW.value


def _alert(
    category: AlertCategory,
    key: str,
    severity: Severity,
    *,
    value: float | None = None,
    params: dict | None = None,
) -> AlertDraft:
    return AlertDraft(
        code=f"satellite.alert.{key}",
        category=category.value,
        severity=severity.value,
        priority=_priority_for(severity.value),
        value=value,
        params=params or {},
    )


def build_alerts(ctx: AlertContext) -> list[AlertDraft]:
    """Deterministic alerts for one session (pure)."""
    alerts: list[AlertDraft] = []

    # Imagery availability
    if ctx.status == SessionStatus.UNAVAILABLE.value:
        if ctx.unavailable_reason == UnavailableReason.CLOUD_COVER.value:
            alerts.append(
                _alert(_C.IMAGERY, "cloud_obstruction", _S.WARNING, value=ctx.cloud_cover)
            )
        elif ctx.unavailable_reason in {
            UnavailableReason.NO_IMAGERY.value,
            UnavailableReason.ACQUISITION_DELAY.value,
            UnavailableReason.PROVIDER_ERROR.value,
            UnavailableReason.PROVIDER_TIMEOUT.value,
            UnavailableReason.PROVIDER_RATE_LIMITED.value,
        }:
            alerts.append(_alert(_C.IMAGERY, "missing_imagery", _S.WARNING))
        elif ctx.unavailable_reason in {
            UnavailableReason.PROCESSING_ERROR.value,
            UnavailableReason.PROVIDER_NOT_CONFIGURED.value,
        }:
            # provider_not_configured is a standing operational gap (no provider
            # credentials wired up), not a transient acquisition failure -- the
            # dashboard's own status card already says "not configured yet"
            # accurately. Reusing "missing_imagery" here ("We will retry on the
            # next pass") told farmers a retry could fix it when nothing short
            # of configuring the provider will -- two contradictory messages on
            # one screen (reported live 2026-08-17). No alert is the honest
            # answer: the status card already covers it, and inventing a second,
            # differently-worded "not configured" alert would just duplicate it.
            return alerts
        return alerts  # no vegetation analysis without a usable scene

    # Available scene with partial cloud → advisory
    if ctx.cloud_cover is not None and ctx.cloud_cover >= CLOUD_ADVISORY:
        alerts.append(_alert(_C.IMAGERY, "cloud_obstruction", _S.ADVICE, value=ctx.cloud_cover))

    # Vegetation trend
    if ctx.ndvi_delta is not None:
        if ctx.ndvi_delta <= NDVI_DELTA_ABNORMAL:
            alerts.append(
                _alert(_C.SEASONAL, "abnormal_seasonal_change", _S.CRITICAL, value=ctx.ndvi_delta)
            )
        elif ctx.ndvi_delta <= NDVI_DELTA_RAPID_DROP:
            alerts.append(
                _alert(_C.VEGETATION, "rapid_ndvi_drop", _S.CRITICAL, value=ctx.ndvi_delta)
            )
        elif ctx.ndvi_delta <= NDVI_DELTA_DECLINING:
            # Declining, but still healthy → an early-warning; otherwise a decline.
            if ctx.ndvi is not None and ctx.ndvi >= NDVI_LOW:
                alerts.append(
                    _alert(
                        _C.VEGETATION,
                        "early_vegetation_decline",
                        _S.ADVICE,
                        value=ctx.ndvi_delta,
                    )
                )
            else:
                alerts.append(
                    _alert(_C.VEGETATION, "vegetation_decline", _S.WARNING, value=ctx.ndvi_delta)
                )

    # Low vigor
    if ctx.ndvi is not None and ctx.ndvi < NDVI_LOW_VIGOR:
        alerts.append(_alert(_C.VEGETATION, "low_vigor", _S.WARNING, value=ctx.ndvi))

    # Moisture stress
    if ctx.ndmi is not None and ctx.ndmi < NDMI_MOISTURE_STRESS:
        alerts.append(_alert(_C.MOISTURE, "moisture_stress", _S.WARNING, value=ctx.ndmi))

    # Large field variation
    if ctx.ndvi_std is not None and ctx.ndvi_std >= NDVI_VARIATION_STD:
        alerts.append(_alert(_C.VARIATION, "large_field_variation", _S.ADVICE, value=ctx.ndvi_std))

    return alerts


def worst_severity(alerts: list[AlertDraft]) -> str | None:
    if not alerts:
        return None
    return max(alerts, key=lambda a: SEVERITY_ORDER.get(a.severity, 0)).severity
