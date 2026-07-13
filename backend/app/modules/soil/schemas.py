"""Soil Intelligence request/response schemas (docs: reuse response envelope).

Recommendations travel as localization ``code``s so the Tamil-first client renders
them. Unavailable values are ``null`` and surfaced honestly — never fabricated.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.soil.constants import DrainageClass, SoilSource
from app.modules.soil.engine import RecommendationDraft, SoilAssessment
from app.modules.soil.models import (
    SoilProfile,
    SoilRecommendation,
    SoilReport,
)


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #
class SoilValuesIn(BaseModel):
    ph: float | None = Field(default=None, ge=0, le=14)
    organic_carbon: float | None = Field(default=None, ge=0, le=100)
    nitrogen: float | None = Field(default=None, ge=0, le=100000)
    phosphorus: float | None = Field(default=None, ge=0, le=100000)
    potassium: float | None = Field(default=None, ge=0, le=100000)
    sulphur: float | None = Field(default=None, ge=0, le=100000)
    ec_salinity: float | None = Field(default=None, ge=0, le=100)
    water_holding_capacity: float | None = Field(default=None, ge=0, le=100)
    drainage: DrainageClass | None = None
    micronutrients: dict[str, float] | None = None


class SoilReportCreate(BaseModel):
    farm_id: uuid.UUID
    source: SoilSource = SoilSource.SELF
    report_url: str | None = Field(default=None, max_length=512)
    thumbnail_url: str | None = Field(default=None, max_length=512)
    mime_type: str | None = Field(default=None, max_length=80)
    lab_name: str | None = Field(default=None, max_length=160)
    test_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)
    values: SoilValuesIn = Field(default_factory=SoilValuesIn)


# --------------------------------------------------------------------------- #
# Outputs
# --------------------------------------------------------------------------- #
class SoilTestResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ph: float | None
    organic_carbon: float | None
    nitrogen: float | None
    phosphorus: float | None
    potassium: float | None
    sulphur: float | None
    ec_salinity: float | None
    water_holding_capacity: float | None
    drainage: str | None
    micronutrients: dict | None


class SoilReportOut(BaseModel):
    id: uuid.UUID
    farm_id: uuid.UUID
    source: str
    report_url: str | None
    thumbnail_url: str | None
    lab_name: str | None
    test_date: date | None
    notes: str | None
    status: str
    confidence: int
    created_at: datetime
    result: SoilTestResultOut | None

    @classmethod
    def from_report(cls, report: SoilReport) -> SoilReportOut:
        return cls(
            id=report.id,
            farm_id=report.farm_id,
            source=report.source,
            report_url=report.report_url,
            thumbnail_url=report.thumbnail_url,
            lab_name=report.lab_name,
            test_date=report.test_date,
            notes=report.notes,
            status=report.status,
            confidence=report.confidence,
            created_at=report.created_at,
            result=(
                SoilTestResultOut.model_validate(report.result) if report.result else None
            ),
        )


class SoilProfileOut(BaseModel):
    id: uuid.UUID
    farm_id: uuid.UUID
    soil_type: str | None
    latitude: float | None
    longitude: float | None
    ph: float | None
    organic_carbon: float | None
    nitrogen: float | None
    phosphorus: float | None
    potassium: float | None
    micronutrients: dict | None
    ec_salinity: float | None
    water_holding_capacity: float | None
    drainage: str | None
    source: str
    confidence: int
    last_test_date: date | None
    updated_at: datetime | None

    @classmethod
    def from_profile(cls, p: SoilProfile) -> SoilProfileOut:
        return cls(
            id=p.id,
            farm_id=p.farm_id,
            soil_type=p.soil_type,
            latitude=p.latitude,
            longitude=p.longitude,
            ph=p.ph,
            organic_carbon=p.organic_carbon,
            nitrogen=p.nitrogen,
            phosphorus=p.phosphorus,
            potassium=p.potassium,
            micronutrients=p.micronutrients,
            ec_salinity=p.ec_salinity,
            water_holding_capacity=p.water_holding_capacity,
            drainage=p.drainage,
            source=p.source,
            confidence=p.confidence,
            last_test_date=p.last_test_date,
            updated_at=p.updated_at,
        )


class SoilAssessmentOut(BaseModel):
    ph_class: str
    organic_carbon: str
    nitrogen: str
    phosphorus: str
    potassium: str
    salinity: str
    deficient_micronutrients: list[str]
    has_any_value: bool

    @classmethod
    def from_assessment(cls, a: SoilAssessment) -> SoilAssessmentOut:
        return cls(
            ph_class=a.ph_class,
            organic_carbon=a.organic_carbon,
            nitrogen=a.nitrogen,
            phosphorus=a.phosphorus,
            potassium=a.potassium,
            salinity=a.salinity,
            deficient_micronutrients=list(a.deficient_micronutrients),
            has_any_value=a.has_any_value,
        )


class SoilRecommendationOut(BaseModel):
    category: str
    code: str
    parameter: str | None
    rating: str | None
    severity: str
    priority: str
    value: float | None
    unit: str | None

    @classmethod
    def from_model(cls, rec: SoilRecommendation) -> SoilRecommendationOut:
        return cls(
            category=rec.category,
            code=rec.code,
            parameter=rec.parameter,
            rating=rec.rating,
            severity=rec.severity,
            priority=rec.priority,
            value=rec.value,
            unit=rec.unit,
        )

    @classmethod
    def from_draft(cls, d: RecommendationDraft) -> SoilRecommendationOut:
        return cls(
            category=d.category,
            code=d.code,
            parameter=d.parameter,
            rating=d.rating,
            severity=d.severity,
            priority=d.priority,
            value=d.value,
            unit=d.unit,
        )


class SoilHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    farm_id: uuid.UUID
    report_id: uuid.UUID | None
    test_date: date | None
    ph: float | None
    organic_carbon: float | None
    nitrogen: float | None
    phosphorus: float | None
    potassium: float | None
    source: str
    confidence: int
    recorded_at: datetime


class SoilDashboardOut(BaseModel):
    """The soil dashboard: profile + assessment + recommendations, or a clear
    'no data' state (soil values are never fabricated)."""

    farm_id: uuid.UUID
    has_data: bool
    message_code: str | None
    profile: SoilProfileOut | None
    assessment: SoilAssessmentOut | None
    recommendations: list[SoilRecommendationOut]
    latest_report: SoilReportOut | None
