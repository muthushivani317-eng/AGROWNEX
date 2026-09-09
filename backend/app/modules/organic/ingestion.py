from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organic.governance import canonical_input_hash
from app.modules.organic.models import OrganicInput


class OrganicInputManifest(BaseModel):
    """Offline/operator manifest. Deliberately not exposed through farmer APIs."""

    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,119}$")
    category: str = Field(min_length=1, max_length=80)
    name_en: str = Field(min_length=1, max_length=180)
    name_ta: str = Field(min_length=1, max_length=180)
    purpose_en: str = Field(min_length=1)
    purpose_ta: str = Field(min_length=1)
    guidance: dict
    applicable_crops: list[str] = Field(default_factory=list)
    applicable_stages: list[str] = Field(default_factory=list)
    applicable_regions: list[str] = Field(default_factory=list)
    limitations: dict = Field(default_factory=dict)
    source_organization: str = Field(min_length=1, max_length=180)
    document_reference: str = Field(min_length=1, max_length=255)
    source_url: str = Field(pattern=r"^https://", max_length=512)
    source_version: str = Field(min_length=1, max_length=80)
    review_status: str = Field(pattern=r"^(draft|approved)$")
    reviewed_by: uuid.UUID | None = None
    reviewed_at: datetime | None = None
    effective_from: date | None = None
    review_due_on: date | None = None

    @model_validator(mode="after")
    def approval_has_operator_review(self):
        if self.review_status == "approved" and not (self.reviewed_by and self.reviewed_at):
            raise ValueError("Approved input requires reviewed_by and reviewed_at")
        if self.review_due_on and self.effective_from and self.review_due_on < self.effective_from:
            raise ValueError("review_due_on must not precede effective_from")
        return self


async def ingest_versioned_input(
    session: AsyncSession, manifest: OrganicInputManifest
) -> OrganicInput:
    """Insert one immutable version from a trusted operator process."""
    existing = await session.scalar(
        select(OrganicInput).where(
            OrganicInput.slug == manifest.slug,
            OrganicInput.source_version == manifest.source_version,
        )
    )
    if existing is not None:
        raise ValueError("ORGANIC_INPUT_VERSION_ALREADY_EXISTS")
    row = OrganicInput(**manifest.model_dump(), content_hash="pending")
    row.content_hash = canonical_input_hash(row)
    session.add(row)
    await session.flush()
    return row
