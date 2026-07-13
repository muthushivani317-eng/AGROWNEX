"""Scheme request/response schemas (docs/API_CONTRACT.md → GOVERNMENT SCHEMES)."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.modules.schemes.constants import FarmerCategory
from app.modules.schemes.engine import EligibilityResult
from app.modules.schemes.models import GovernmentScheme, SchemeDocument
from app.schemas.response import PaginatedData


class EligibilityOut(BaseModel):
    """The engine's verdict for a scheme + farmer (transparent + explainable)."""

    status: str
    score: int
    matched: list[str]
    unmet: list[str]
    unknown: list[str]

    @classmethod
    def from_result(cls, result: EligibilityResult) -> EligibilityOut:
        return cls(
            status=result.status,
            score=result.score,
            matched=result.matched,
            unmet=result.unmet,
            unknown=result.unknown,
        )


class DocumentOut(BaseModel):
    name: str
    required: bool

    @classmethod
    def from_row(cls, doc: SchemeDocument) -> DocumentOut:
        return cls(name=doc.document_name, required=doc.is_required)


class SchemeSummaryOut(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    category: str
    description: str
    departments: list[str]
    state: str
    official_url: str | None
    last_date: date | None
    status: str
    bookmarked: bool = False
    eligibility: EligibilityOut | None = None

    @classmethod
    def from_scheme(
        cls,
        scheme: GovernmentScheme,
        *,
        bookmarked: bool = False,
        eligibility: EligibilityResult | None = None,
    ) -> SchemeSummaryOut:
        return cls(
            id=scheme.id,
            slug=scheme.slug,
            title=scheme.title,
            category=scheme.category,
            description=scheme.description,
            departments=scheme.departments or [],
            state=scheme.state,
            official_url=scheme.official_url,
            last_date=scheme.last_date,
            status=scheme.status,
            bookmarked=bookmarked,
            eligibility=(
                EligibilityOut.from_result(eligibility) if eligibility else None
            ),
        )


class SchemeDetailOut(SchemeSummaryOut):
    benefits: str | None = None
    eligibility_summary: str | None = None
    application_steps: list[str] = Field(default_factory=list)
    documents: list[DocumentOut] = Field(default_factory=list)
    source: str | None = None
    verified_at: datetime | None = None

    @classmethod
    def from_detail(
        cls,
        scheme: GovernmentScheme,
        *,
        documents: list[SchemeDocument],
        bookmarked: bool = False,
        eligibility: EligibilityResult | None = None,
    ) -> SchemeDetailOut:
        return cls(
            id=scheme.id,
            slug=scheme.slug,
            title=scheme.title,
            category=scheme.category,
            description=scheme.description,
            departments=scheme.departments or [],
            state=scheme.state,
            official_url=scheme.official_url,
            last_date=scheme.last_date,
            status=scheme.status,
            bookmarked=bookmarked,
            eligibility=(
                EligibilityOut.from_result(eligibility) if eligibility else None
            ),
            benefits=scheme.benefits,
            eligibility_summary=scheme.eligibility_summary,
            application_steps=scheme.application_steps or [],
            documents=[DocumentOut.from_row(d) for d in documents],
            source=scheme.source,
            verified_at=scheme.verified_at,
        )


class EligibilityQuery(BaseModel):
    """Optional overrides for the eligibility check (defaults from profile + farm)."""

    farm_id: uuid.UUID | None = None
    state: str | None = Field(default=None, max_length=80)
    district: str | None = Field(default=None, max_length=80)
    crop: str | None = Field(default=None, max_length=80)
    land_hectares: float | None = Field(default=None, ge=0, le=100000)
    annual_income: int | None = Field(default=None, ge=0)
    farmer_category: FarmerCategory | None = None


class BookmarkRequest(BaseModel):
    scheme_id: uuid.UUID


class SchemePageMeta(BaseModel):
    """Context echoed back so the client can show what the ranking was based on."""

    district: str | None = None
    crop: str | None = None
    land_hectares: float | None = None
    farmer_category: str | None = None


class EligibleSchemesOut(BaseModel):
    """Eligible schemes (paginated, ranked) + the context the ranking used."""

    results: PaginatedData[SchemeSummaryOut]
    context: SchemePageMeta


class RecommendedSchemesOut(BaseModel):
    items: list[SchemeSummaryOut] = Field(default_factory=list)
    context: SchemePageMeta
