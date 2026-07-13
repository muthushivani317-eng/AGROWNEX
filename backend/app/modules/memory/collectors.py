"""Deterministic memory collectors (pure — docs: deterministic memory generation).

One collector per structured event a module can emit. Each is a pure function of
primitive inputs (extracted from the source module's own records by ``sources.py``)
and returns a ``MemoryEventDraft`` — or ``None`` when there is nothing real to
remember. No collector fabricates data (docs/PRODUCT_RULES.md).
"""
from __future__ import annotations

from datetime import datetime

from app.modules.memory.constants import (
    EventType,
    Importance,
    ObservationKind,
    SourceModule,
)
from app.modules.memory.signals import MemoryEventDraft

_CODE = "memory.event"


# --------------------------------------------------------------------------- #
# Disease
# --------------------------------------------------------------------------- #
_DISEASE_IMPORTANCE = {
    "high": Importance.CRITICAL.value,
    "moderate": Importance.HIGH.value,
    "low": Importance.MEDIUM.value,
    "none": Importance.LOW.value,
}


def collect_disease(
    *,
    occurred_at: datetime,
    disease: str | None,
    confidence: int | None,
    severity: str | None,
    crop: str | None,
    needs_expert: bool,
    source_ref: str | None,
) -> MemoryEventDraft | None:
    if not disease:
        return None
    importance = _DISEASE_IMPORTANCE.get((severity or "").lower(), Importance.MEDIUM.value)
    tags = ["disease", severity or "unknown"]
    if needs_expert:
        tags.append("needs_expert")
    return MemoryEventDraft(
        source_module=SourceModule.DISEASE.value,
        event_type=EventType.DISEASE_DIAGNOSED.value,
        occurred_at=occurred_at,
        summary=f"{_CODE}.disease_diagnosed",
        importance=importance,
        observation=ObservationKind.OBSERVED.value,
        confidence=confidence,
        crop=crop,
        source_ref=source_ref,
        params={"disease": disease, "severity": severity, "confidence": confidence},
        detail=f"Disease '{disease}' diagnosed (severity {severity}, {confidence}% confidence).",
        tags=tuple(tags),
    )


# --------------------------------------------------------------------------- #
# Nutrient
# --------------------------------------------------------------------------- #
def collect_nutrient(
    *,
    occurred_at: datetime,
    primary: str | None,
    status: str | None,
    confidence: int | None,
    severity: str | None,
    crop: str | None,
    needs_test: bool,
    source_ref: str | None,
) -> MemoryEventDraft | None:
    if not primary or status not in ("confirmed", "possible"):
        return None
    if status == "confirmed" and severity == "severe":
        importance = Importance.HIGH.value
    elif status == "confirmed":
        importance = Importance.MEDIUM.value
    else:
        importance = Importance.LOW.value
    observation = (
        ObservationKind.OBSERVED.value
        if status == "confirmed"
        else ObservationKind.INFERRED.value
    )
    tags = ["nutrient", primary, status]
    if needs_test:
        tags.append("needs_test")
    return MemoryEventDraft(
        source_module=SourceModule.NUTRIENT.value,
        event_type=EventType.NUTRIENT_DEFICIENCY_DETECTED.value,
        occurred_at=occurred_at,
        summary=f"{_CODE}.nutrient_deficiency_detected",
        importance=importance,
        observation=observation,
        confidence=confidence,
        crop=crop,
        source_ref=source_ref,
        params={"nutrient": primary, "status": status, "severity": severity},
        detail=f"Nutrient deficiency '{primary}' {status} (severity {severity}).",
        tags=tuple(tags),
    )


# --------------------------------------------------------------------------- #
# Soil
# --------------------------------------------------------------------------- #
def collect_soil(
    *,
    occurred_at: datetime,
    source: str | None,
    confidence: int | None,
    crop: str | None,
    source_ref: str | None,
) -> MemoryEventDraft:
    return MemoryEventDraft(
        source_module=SourceModule.SOIL.value,
        event_type=EventType.SOIL_REPORT_UPLOADED.value,
        occurred_at=occurred_at,
        summary=f"{_CODE}.soil_report_uploaded",
        importance=Importance.MEDIUM.value,
        observation=ObservationKind.OBSERVED.value,
        confidence=confidence,
        crop=crop,
        source_ref=source_ref,
        params={"source": source},
        detail=f"Soil report processed (source {source}).",
        tags=("soil", source or "self"),
    )


# --------------------------------------------------------------------------- #
# Satellite
# --------------------------------------------------------------------------- #
def collect_satellite(
    *,
    occurred_at: datetime,
    vegetation_health: str | None,
    trend: str | None,
    stress_level: str | None,
    declining: bool,
    ndvi: float | None,
    crop: str | None,
    source_ref: str | None,
) -> MemoryEventDraft:
    if declining:
        importance = (
            Importance.HIGH.value if stress_level == "severe" else Importance.MEDIUM.value
        )
        return MemoryEventDraft(
            source_module=SourceModule.SATELLITE.value,
            event_type=EventType.SATELLITE_VEGETATION_DECLINE.value,
            occurred_at=occurred_at,
            summary=f"{_CODE}.satellite_vegetation_decline",
            importance=importance,
            observation=ObservationKind.INFERRED.value,
            crop=crop,
            source_ref=source_ref,
            params={"vegetation_health": vegetation_health, "trend": trend, "ndvi": ndvi},
            detail=f"Satellite vegetation decline (health {vegetation_health}, trend {trend}).",
            tags=("satellite", "decline"),
        )
    return MemoryEventDraft(
        source_module=SourceModule.SATELLITE.value,
        event_type=EventType.SATELLITE_SCAN.value,
        occurred_at=occurred_at,
        summary=f"{_CODE}.satellite_scan",
        importance=Importance.LOW.value,
        observation=ObservationKind.INFERRED.value,
        crop=crop,
        source_ref=source_ref,
        params={"vegetation_health": vegetation_health, "trend": trend, "ndvi": ndvi},
        detail=f"Satellite scan recorded (health {vegetation_health}).",
        tags=("satellite", "scan"),
    )


# --------------------------------------------------------------------------- #
# Growth
# --------------------------------------------------------------------------- #
def collect_growth(
    *,
    occurred_at: datetime,
    health_score: int | None,
    health_delta: int | None,
    risk_level: str | None,
    crop: str | None,
    source_ref: str | None,
) -> MemoryEventDraft:
    declining = risk_level == "high" or (health_delta or 0) <= -5
    if declining:
        return MemoryEventDraft(
            source_module=SourceModule.GROWTH.value,
            event_type=EventType.GROWTH_DECLINE.value,
            occurred_at=occurred_at,
            summary=f"{_CODE}.growth_decline",
            importance=Importance.MEDIUM.value,
            observation=ObservationKind.OBSERVED.value,
            confidence=health_score,
            crop=crop,
            source_ref=source_ref,
            params={"health_score": health_score, "health_delta": health_delta, "risk": risk_level},
            detail=f"Tracked crop health declined (score {health_score}, delta {health_delta}).",
            tags=("growth", "decline"),
        )
    return MemoryEventDraft(
        source_module=SourceModule.GROWTH.value,
        event_type=EventType.GROWTH_TRACKED.value,
        occurred_at=occurred_at,
        summary=f"{_CODE}.growth_tracked",
        importance=Importance.LOW.value,
        observation=ObservationKind.OBSERVED.value,
        confidence=health_score,
        crop=crop,
        source_ref=source_ref,
        params={"health_score": health_score, "risk": risk_level},
        detail=f"Crop growth tracked (health score {health_score}).",
        tags=("growth", "tracked"),
    )


# --------------------------------------------------------------------------- #
# Weather (best-effort, inferred from the verified forecast)
# --------------------------------------------------------------------------- #
_WEATHER_HIGH = {"heavy_rain.severe", "heat_stress.extreme", "cold.frost"}


def collect_weather(
    *,
    occurred_at: datetime,
    insight_codes: tuple[str, ...],
    crop: str | None,
) -> MemoryEventDraft | None:
    notable = [
        c for c in insight_codes if c.startswith(("heavy_rain", "heat_stress", "cold", "wind"))
    ]
    if not notable:
        return None
    importance = (
        Importance.HIGH.value
        if any(c in _WEATHER_HIGH for c in notable)
        else Importance.MEDIUM.value
    )
    return MemoryEventDraft(
        source_module=SourceModule.WEATHER.value,
        event_type=EventType.WEATHER_EVENT.value,
        occurred_at=occurred_at,
        summary=f"{_CODE}.weather_event",
        importance=importance,
        observation=ObservationKind.INFERRED.value,
        crop=crop,
        params={"codes": notable},
        detail=f"Notable weather expected: {', '.join(notable)}.",
        tags=("weather", *[c.split(".")[0] for c in notable]),
    )


# --------------------------------------------------------------------------- #
# Calendar / Harvest
# --------------------------------------------------------------------------- #
def collect_calendar_completed(
    *,
    occurred_at: datetime,
    completed_count: int,
    crop: str | None,
) -> MemoryEventDraft | None:
    if completed_count <= 0:
        return None
    return MemoryEventDraft(
        source_module=SourceModule.CALENDAR.value,
        event_type=EventType.CALENDAR_COMPLETED.value,
        occurred_at=occurred_at,
        summary=f"{_CODE}.crop_calendar_completed",
        importance=Importance.LOW.value,
        observation=ObservationKind.OBSERVED.value,
        crop=crop,
        params={"count": completed_count},
        detail=f"{completed_count} crop-calendar task(s) completed.",
        tags=("calendar", "completed"),
    )


def collect_harvest(
    *,
    occurred_at: datetime,
    crop: str | None,
    quantity: float | None,
    unit: str | None,
    source_ref: str | None,
) -> MemoryEventDraft:
    return MemoryEventDraft(
        source_module=SourceModule.PRODUCE.value,
        event_type=EventType.HARVEST_SUBMITTED.value,
        occurred_at=occurred_at,
        summary=f"{_CODE}.harvest_submitted",
        importance=Importance.HIGH.value,
        observation=ObservationKind.OBSERVED.value,
        crop=crop,
        source_ref=source_ref,
        params={"quantity": quantity, "unit": unit},
        detail=f"Harvest submitted for {crop} ({quantity} {unit}).",
        tags=("produce", "harvest"),
    )


# --------------------------------------------------------------------------- #
# Expert
# --------------------------------------------------------------------------- #
def collect_expert(
    *,
    occurred_at: datetime,
    resolved: bool,
    subject: str | None,
    crop: str | None,
    source_ref: str | None,
) -> MemoryEventDraft:
    if resolved:
        return MemoryEventDraft(
            source_module=SourceModule.EXPERTS.value,
            event_type=EventType.EXPERT_CONSULTATION_RESOLVED.value,
            occurred_at=occurred_at,
            summary=f"{_CODE}.expert_consultation_resolved",
            importance=Importance.MEDIUM.value,
            observation=ObservationKind.OBSERVED.value,
            crop=crop,
            source_ref=source_ref,
            params={"subject": subject},
            detail=f"Expert consultation resolved: {subject}.",
            tags=("experts", "resolved"),
        )
    return MemoryEventDraft(
        source_module=SourceModule.EXPERTS.value,
        event_type=EventType.EXPERT_CONSULTATION_OPENED.value,
        occurred_at=occurred_at,
        summary=f"{_CODE}.expert_consultation_opened",
        importance=Importance.LOW.value,
        observation=ObservationKind.OBSERVED.value,
        crop=crop,
        source_ref=source_ref,
        params={"subject": subject},
        detail=f"Expert consultation opened: {subject}.",
        tags=("experts", "opened"),
    )


# --------------------------------------------------------------------------- #
# Government scheme
# --------------------------------------------------------------------------- #
def collect_scheme(
    *,
    occurred_at: datetime,
    title: str | None,
    source_ref: str | None,
) -> MemoryEventDraft:
    return MemoryEventDraft(
        source_module=SourceModule.SCHEMES.value,
        event_type=EventType.GOVERNMENT_SCHEME_SAVED.value,
        occurred_at=occurred_at,
        summary=f"{_CODE}.government_scheme_saved",
        importance=Importance.LOW.value,
        observation=ObservationKind.OBSERVED.value,
        source_ref=source_ref,
        params={"scheme": title},
        detail=f"Government scheme saved: {title}.",
        tags=("schemes", "saved"),
    )


# --------------------------------------------------------------------------- #
# Market
# --------------------------------------------------------------------------- #
def collect_market(
    *,
    occurred_at: datetime,
    crop: str | None,
    source_ref: str | None,
) -> MemoryEventDraft:
    return MemoryEventDraft(
        source_module=SourceModule.MARKET.value,
        event_type=EventType.MARKET_PRICE_VIEWED.value,
        occurred_at=occurred_at,
        summary=f"{_CODE}.market_price_viewed",
        importance=Importance.LOW.value,
        observation=ObservationKind.OBSERVED.value,
        crop=crop,
        source_ref=source_ref,
        params={"crop": crop},
        detail=f"Market price watched for {crop}.",
        tags=("market", "watch"),
    )


# --------------------------------------------------------------------------- #
# AI Chat
# --------------------------------------------------------------------------- #
def collect_ai_chat(
    *,
    occurred_at: datetime,
    title: str | None,
    source_ref: str | None,
) -> MemoryEventDraft:
    return MemoryEventDraft(
        source_module=SourceModule.AI_CHAT.value,
        event_type=EventType.AI_CONVERSATION.value,
        occurred_at=occurred_at,
        summary=f"{_CODE}.ai_conversation",
        importance=Importance.LOW.value,
        observation=ObservationKind.OBSERVED.value,
        source_ref=source_ref,
        params={"title": title},
        detail=f"AI conversation: {title}.",
        tags=("ai_chat",),
    )
