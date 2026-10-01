"""Farm request/response schemas (docs/API_CONTRACT.md → FARM MODULE)."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.farms.constants import (
    AreaSource,
    BoundarySource,
    FarmStatus,
    IrrigationType,
    LocationSource,
    SoilType,
    WaterSource,
)
from app.modules.farms.geo import InvalidPolygonError, extract_ring, validate_ring
from app.modules.farms.models import Farm
from app.shared.url_safety import HttpsUrl


# --------------------------------------------------------------------------- #
# Sub-objects
# --------------------------------------------------------------------------- #
class LocationIn(BaseModel):
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    accuracy: float | None = Field(default=None, ge=0)
    elevation: float | None = None
    address: str | None = Field(default=None, max_length=255)
    district: str | None = Field(default=None, max_length=80)
    block: str | None = Field(default=None, max_length=80)
    village: str | None = Field(default=None, max_length=80)
    source: LocationSource = LocationSource.GPS


class BoundaryIn(BaseModel):
    geojson: dict[str, Any]
    source: BoundarySource = BoundarySource.DRAWN

    @field_validator("geojson")
    @classmethod
    def _validate_polygon(cls, value: dict[str, Any]) -> dict[str, Any]:
        try:
            validate_ring(extract_ring(value))
        except InvalidPolygonError as exc:
            raise ValueError(str(exc)) from exc
        return value


# --------------------------------------------------------------------------- #
# Farm write (POST / PUT share the same body)
# --------------------------------------------------------------------------- #
class FarmWrite(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    crop: str | None = Field(default=None, max_length=80)
    crop_variety: str | None = Field(default=None, max_length=120)
    sowing_date: date | None = None
    soil_type: SoilType | None = None
    irrigation_type: IrrigationType | None = None
    water_source: WaterSource | None = None
    status: FarmStatus = FarmStatus.ACTIVE
    notes: str | None = Field(default=None, max_length=2000)
    area_hectares: float | None = Field(default=None, gt=0, le=100_000)
    area_source: AreaSource = AreaSource.AUTO
    location: LocationIn | None = None
    boundary: BoundaryIn | None = None


# --------------------------------------------------------------------------- #
# Farm media
# --------------------------------------------------------------------------- #
class FarmMediaCreate(BaseModel):
    file_url: HttpsUrl = Field(min_length=1, max_length=512)
    file_name: str | None = Field(default=None, max_length=255)
    mime_type: str | None = Field(default=None, max_length=80)
    file_size: int | None = Field(default=None, ge=0)
    caption: str | None = Field(default=None, max_length=255)


class FarmMediaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_url: str
    file_name: str | None
    mime_type: str | None
    file_size: int | None
    caption: str | None
    created_at: datetime


# --------------------------------------------------------------------------- #
# Read models
# --------------------------------------------------------------------------- #
class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    latitude: float | None
    longitude: float | None
    accuracy: float | None
    elevation: float | None
    address: str | None
    district: str | None
    block: str | None
    village: str | None
    source: str


class BoundaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    geojson: dict[str, Any] | None
    area_hectares: float | None
    perimeter_m: float | None
    centroid_lat: float | None
    centroid_lng: float | None
    vertex_count: int | None
    source: str


class FarmOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    crop: str | None
    crop_variety: str | None
    sowing_date: date | None
    soil_type: str | None
    irrigation_type: str | None
    water_source: str | None
    area_hectares: float | None
    area_source: str
    notes: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    location: LocationOut | None
    boundary: BoundaryOut | None
    images: list[FarmMediaOut]
    image_count: int

    @classmethod
    def from_farm(cls, farm: Farm) -> FarmOut:
        images = [FarmMediaOut.model_validate(m) for m in farm.media]
        return cls(
            id=farm.id,
            user_id=farm.user_id,
            name=farm.name,
            crop=farm.crop,
            crop_variety=farm.crop_variety,
            sowing_date=farm.sowing_date,
            soil_type=farm.soil_type,
            irrigation_type=farm.irrigation_type,
            water_source=farm.water_source,
            area_hectares=farm.area_hectares,
            area_source=farm.area_source,
            notes=farm.notes,
            status=farm.status,
            created_at=farm.created_at,
            updated_at=farm.updated_at,
            location=LocationOut.model_validate(farm.location) if farm.location else None,
            boundary=BoundaryOut.model_validate(farm.boundary) if farm.boundary else None,
            images=images,
            image_count=len(images),
        )


class FarmSummaryOut(BaseModel):
    id: uuid.UUID
    name: str
    crop: str | None
    status: str
    area_hectares: float | None
    district: str | None
    has_boundary: bool
    centroid_lat: float | None
    centroid_lng: float | None
    latitude: float | None
    longitude: float | None
    image_count: int
    updated_at: datetime

    @classmethod
    def from_farm(cls, farm: Farm) -> FarmSummaryOut:
        location = farm.location
        boundary = farm.boundary
        return cls(
            id=farm.id,
            name=farm.name,
            crop=farm.crop,
            status=farm.status,
            area_hectares=farm.area_hectares,
            district=location.district if location else None,
            has_boundary=boundary is not None and boundary.geojson is not None,
            centroid_lat=boundary.centroid_lat if boundary else None,
            centroid_lng=boundary.centroid_lng if boundary else None,
            latitude=location.latitude if location else None,
            longitude=location.longitude if location else None,
            image_count=len(farm.media),
            updated_at=farm.updated_at,
        )
