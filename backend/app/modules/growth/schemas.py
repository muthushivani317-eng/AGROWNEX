"""Growth request/response schemas (docs/API_CONTRACT.md → CROP GROWTH)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.modules.growth.models import (
    CropGrowthAnalysis,
    CropGrowthImage,
    CropGrowthSession,
    CropGrowthTimeline,
)

_MIME_PATTERN = "^image/(jpeg|png|webp)$"


class UploadGrowthRequest(BaseModel):
    image_base64: str = Field(min_length=16, max_length=24_000_000)
    mime_type: str = Field(pattern=_MIME_PATTERN)
    farm_id: uuid.UUID
    # Append to an existing monitoring session, or omit to reuse/create one.
    session_id: uuid.UUID | None = None
    crop: str | None = Field(default=None, max_length=80)
    variety: str | None = Field(default=None, max_length=80)
    language: str | None = Field(default=None, pattern="^(ta|en)$")
    capture_method: str | None = Field(default=None, pattern="^(camera|gallery)$")
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    notes: str | None = Field(default=None, max_length=500)


class GrowthAnalysisOut(BaseModel):
    growth_stage: str
    plant_vigor: str
    health_score: int | None
    confidence: int | None
    leaf_color_observations: list[str]
    visible_abnormalities: list[str]
    changes_from_previous: list[str]
    recommendations: list[str]
    disease_result: dict | None
    nutrient_result: dict | None
    needs_expert_review: bool
    growth_summary_tamil: str | None
    growth_summary_english: str | None
    model_used: str | None

    @classmethod
    def from_row(cls, row: CropGrowthAnalysis | None) -> GrowthAnalysisOut | None:
        if row is None:
            return None
        return cls(
            growth_stage=row.growth_stage,
            plant_vigor=row.plant_vigor,
            health_score=row.health_score,
            confidence=row.confidence,
            leaf_color_observations=row.leaf_color_observations or [],
            visible_abnormalities=row.visible_abnormalities or [],
            changes_from_previous=row.changes_from_previous or [],
            recommendations=row.recommendations or [],
            disease_result=row.disease_result,
            nutrient_result=row.nutrient_result,
            needs_expert_review=row.needs_expert_review,
            growth_summary_tamil=row.growth_summary_tamil,
            growth_summary_english=row.growth_summary_english,
            model_used=row.model_used,
        )


class GrowthImageOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    farm_id: uuid.UUID | None
    image_url: str
    thumbnail_url: str | None
    capture_method: str
    captured_at: datetime
    week_number: int
    latitude: float | None
    longitude: float | None
    weather_snapshot: dict | None
    image_quality: dict | None
    notes: str | None
    created_at: datetime
    analysis: GrowthAnalysisOut | None = None

    @classmethod
    def from_row(
        cls,
        image: CropGrowthImage,
        *,
        analysis: CropGrowthAnalysis | None = None,
    ) -> GrowthImageOut:
        return cls(
            id=image.id,
            session_id=image.session_id,
            farm_id=image.farm_id,
            image_url=image.image_url,
            thumbnail_url=image.thumbnail_url,
            capture_method=image.capture_method,
            captured_at=image.captured_at,
            week_number=image.week_number,
            latitude=image.latitude,
            longitude=image.longitude,
            weather_snapshot=image.weather_snapshot,
            image_quality=image.image_quality,
            notes=image.notes,
            created_at=image.created_at,
            analysis=GrowthAnalysisOut.from_row(analysis),
        )


class TimelineEntryOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    image_id: uuid.UUID
    week_number: int
    growth_stage: str
    health_score: int | None
    health_delta: int | None
    risk_level: str
    summary: str | None
    recorded_at: datetime
    image_url: str | None = None
    thumbnail_url: str | None = None

    @classmethod
    def from_row(
        cls, entry: CropGrowthTimeline, *, image: CropGrowthImage | None = None
    ) -> TimelineEntryOut:
        return cls(
            id=entry.id,
            session_id=entry.session_id,
            image_id=entry.image_id,
            week_number=entry.week_number,
            growth_stage=entry.growth_stage,
            health_score=entry.health_score,
            health_delta=entry.health_delta,
            risk_level=entry.risk_level,
            summary=entry.summary,
            recorded_at=entry.recorded_at,
            image_url=image.image_url if image else None,
            thumbnail_url=image.thumbnail_url if image else None,
        )


class GrowthSessionOut(BaseModel):
    id: uuid.UUID
    farm_id: uuid.UUID
    crop: str | None
    variety: str | None
    title: str | None
    sowing_date: date | None
    status: str
    current_growth_stage: str
    latest_health_score: int | None
    latest_risk_level: str | None
    image_count: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, session: CropGrowthSession) -> GrowthSessionOut:
        return cls(
            id=session.id,
            farm_id=session.farm_id,
            crop=session.crop,
            variety=session.variety,
            title=session.title,
            sowing_date=session.sowing_date,
            status=session.status,
            current_growth_stage=session.current_growth_stage,
            latest_health_score=session.latest_health_score,
            latest_risk_level=session.latest_risk_level,
            image_count=session.image_count,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )


class GrowthSessionDetailOut(GrowthSessionOut):
    images: list[GrowthImageOut] = Field(default_factory=list)
    timeline: list[TimelineEntryOut] = Field(default_factory=list)


class GrowthTimelineOut(BaseModel):
    session: GrowthSessionOut
    timeline: list[TimelineEntryOut] = Field(default_factory=list)


class UploadResultOut(BaseModel):
    session: GrowthSessionOut
    image: GrowthImageOut
    timeline_entry: TimelineEntryOut


class StageEvidenceIn(BaseModel):
    registry_verified: bool = False
    registry_version: str | None = Field(default=None, max_length=80)
    planting_date_present: bool = False
    weather_source: str | None = Field(default=None, pattern="^(live|cached|stale|missing)$")
    image_observation: str | None = Field(default=None, max_length=80)
    suggested_stage: str | None = Field(default=None, max_length=20)
    supports: list[str] = Field(default_factory=list, max_length=20)
    conflicts: list[str] = Field(default_factory=list, max_length=20)
    missing: list[str] = Field(default_factory=list, max_length=20)


class StageTransitionRequest(BaseModel):
    farm_id: uuid.UUID
    crop_cycle_id: str = Field(min_length=1, max_length=80)
    event: str = Field(pattern="^(evaluate|confirm|correct|complete)$")
    stage: str | None = Field(default=None, max_length=20)
    expected_version: int | None = Field(default=None, ge=1)
    idempotency_key: str = Field(min_length=8, max_length=100)
    evidence: StageEvidenceIn = Field(default_factory=StageEvidenceIn)
    reason: str | None = Field(default=None, max_length=500)
    photo_reference: str | None = Field(default=None, max_length=512)
    expert_reviewed: bool = False
    allow_large_jump: bool = False


class StageStateOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    farm_id: uuid.UUID
    crop_cycle_id: str
    state: str
    suggested_stage: str | None
    confirmed_stage: str | None
    registry_version: str | None
    calculation_version: str
    version: int
    pending_sync: bool
    evidence_snapshot: dict
    updated_at: datetime


class StageTransitionOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    event: str
    prior_state: str | None
    next_state: str
    prior_stage: str | None
    stage: str | None
    reason: str | None
    photo_reference: str | None
    registry_version: str | None
    evidence_snapshot: dict
    expert_reviewed: bool
    created_at: datetime
