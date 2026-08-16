"""Shared provider data shapes.

Split out from ``provider.py`` so that ``curated_data.py`` (real, hand-verified
scheme content) and ``provider.py`` (the provider classes that serve it) can
both depend on these types without a circular import between the two.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.modules.schemes.constants import ANY, SchemeStatus


@dataclass(frozen=True)
class ProviderDocument:
    name: str
    required: bool = True


@dataclass(frozen=True)
class ProviderScheme:
    """A normalized, verified scheme record, independent of the upstream source."""

    slug: str
    title: str
    category: str
    description: str
    benefits: str
    eligibility_summary: str
    application_steps: list[str]
    departments: list[str]
    official_url: str
    documents: list[ProviderDocument]
    source: str
    state: str = "all"
    start_date: date | None = None
    last_date: date | None = None
    status: str = SchemeStatus.ACTIVE.value
    # Structured rules (["all"] means no constraint).
    states: list[str] = field(default_factory=lambda: [ANY])
    districts: list[str] = field(default_factory=lambda: [ANY])
    crops: list[str] = field(default_factory=lambda: [ANY])
    farmer_categories: list[str] = field(default_factory=lambda: [ANY])
    min_land_hectares: float | None = None
    max_land_hectares: float | None = None
    max_annual_income: int | None = None
