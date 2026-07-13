"""Satellite Intelligence schemas (docs: reuse response envelope). Unavailable
imagery is reported honestly; indices are never fabricated."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.modules.satellite.models import (
    SatelliteAlert,
    SatelliteIndex,
    SatelliteSession,
)


class SatelliteIndexOut(BaseModel):
    index_name: str
    mean: float | None
    minimum: float | None
    maximum: float | None
    std: float | None

    @classmethod
    def from_model(cls, m: SatelliteIndex) -> SatelliteIndexOut:
        return cls(
            index_name=m.index_name,
            mean=m.mean,
            minimum=m.minimum,
            maximum=m.maximum,
            std=m.std,
        )


class SatelliteImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    band: str
    image_url: str
    thumbnail_url: str | None
    resolution_m: float | None


class SatelliteAlertOut(BaseModel):
    code: str
    category: str
    severity: str
    priority: str
    value: float | None
    params: dict

    @classmethod
    def from_model(cls, m: SatelliteAlert) -> SatelliteAlertOut:
        return cls(
            code=m.code,
            category=m.category,
            severity=m.severity,
            priority=m.priority,
            value=m.value,
            params=m.params or {},
        )


class SatelliteSessionOut(BaseModel):
    id: uuid.UUID
    farm_id: uuid.UUID
    provider: str
    status: str
    unavailable_reason: str
    is_sample: bool
    capture_date: date | None
    cloud_cover: float | None
    resolution_m: float | None
    ndvi: float | None
    ndre: float | None
    evi: float | None
    ndmi: float | None
    vegetation_health: str | None
    stress_level: str | None
    moisture_status: str | None
    trend: str | None
    ndvi_delta: float | None
    confidence: int
    metadata: dict | None
    created_at: datetime
    images: list[SatelliteImageOut]
    indices: list[SatelliteIndexOut]
    alerts: list[SatelliteAlertOut]

    @classmethod
    def from_session(cls, s: SatelliteSession) -> SatelliteSessionOut:
        return cls(
            id=s.id,
            farm_id=s.farm_id,
            provider=s.provider,
            status=s.status,
            unavailable_reason=s.unavailable_reason,
            is_sample=s.is_sample,
            capture_date=s.capture_date,
            cloud_cover=s.cloud_cover,
            resolution_m=s.resolution_m,
            ndvi=s.ndvi,
            ndre=s.ndre,
            evi=s.evi,
            ndmi=s.ndmi,
            vegetation_health=s.vegetation_health,
            stress_level=s.stress_level,
            moisture_status=s.moisture_status,
            trend=s.trend,
            ndvi_delta=s.ndvi_delta,
            confidence=s.confidence,
            metadata=s.session_metadata,
            created_at=s.created_at,
            images=[SatelliteImageOut.model_validate(i) for i in (s.images or [])],
            indices=[SatelliteIndexOut.from_model(i) for i in (s.indices or [])],
            alerts=[SatelliteAlertOut.from_model(a) for a in (s.alerts or [])],
        )


class SatelliteDashboardOut(BaseModel):
    farm_id: uuid.UUID
    has_polygon: bool
    has_data: bool
    status: str
    unavailable_reason: str
    message_code: str | None
    session: SatelliteSessionOut | None
    alerts: list[SatelliteAlertOut]


class SatelliteHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    farm_id: uuid.UUID
    session_id: uuid.UUID | None
    capture_date: date | None
    ndvi: float | None
    ndre: float | None
    evi: float | None
    ndmi: float | None
    vegetation_health: str | None
    stress_level: str | None
    moisture_status: str | None
    source: str
    confidence: int
    recorded_at: datetime


class TimelinePointOut(BaseModel):
    period: str
    ndvi: float | None
    ndre: float | None
    ndmi: float | None
    count: int


class SatelliteTimelineOut(BaseModel):
    farm_id: uuid.UUID
    range: str
    points: list[TimelinePointOut]
