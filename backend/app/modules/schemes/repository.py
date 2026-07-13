"""Scheme repository (docs/BACKEND_ARCHITECTURE.md → Repository Pattern).

The only layer that queries the scheme tables. Handles provider seeding
(idempotent upsert by slug), filtered listing, document lookups and user-scoped
bookmarks. No SQL lives in routes or the service.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.schemes.constants import SchemeStatus
from app.modules.schemes.models import (
    GovernmentScheme,
    SchemeBookmark,
    SchemeDocument,
)
from app.modules.schemes.provider import ProviderScheme


class SchemeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ----------------------------------------------------------------- #
    # Seeding (provider → DB, idempotent by slug)
    # ----------------------------------------------------------------- #
    async def count(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(GovernmentScheme)
        )
        return int(result.scalar_one())

    async def get_by_slug(self, slug: str) -> GovernmentScheme | None:
        result = await self.session.execute(
            select(GovernmentScheme).where(GovernmentScheme.slug == slug)
        )
        return result.scalar_one_or_none()

    async def upsert_scheme(self, record: ProviderScheme) -> GovernmentScheme:
        scheme = await self.get_by_slug(record.slug)
        verified = datetime.now(UTC)
        if scheme is None:
            scheme = GovernmentScheme(slug=record.slug)
            self.session.add(scheme)
        scheme.title = record.title
        scheme.category = record.category
        scheme.description = record.description
        scheme.benefits = record.benefits
        scheme.eligibility_summary = record.eligibility_summary
        scheme.application_steps = record.application_steps
        scheme.departments = record.departments
        scheme.official_url = record.official_url
        scheme.state = record.state
        scheme.start_date = record.start_date
        scheme.last_date = record.last_date
        scheme.status = record.status
        scheme.source = record.source
        scheme.verified_at = verified
        scheme.states = record.states
        scheme.districts = record.districts
        scheme.crops = record.crops
        scheme.farmer_categories = record.farmer_categories
        scheme.min_land_hectares = record.min_land_hectares
        scheme.max_land_hectares = record.max_land_hectares
        scheme.max_annual_income = record.max_annual_income
        scheme.is_deleted = False
        await self.session.flush()

        await self._replace_documents(scheme.id, record)
        return scheme

    async def _replace_documents(
        self, scheme_id: uuid.UUID, record: ProviderScheme
    ) -> None:
        existing = (
            await self.session.execute(
                select(SchemeDocument).where(SchemeDocument.scheme_id == scheme_id)
            )
        ).scalars().all()
        for doc in existing:
            await self.session.delete(doc)
        await self.session.flush()
        for order, doc in enumerate(record.documents):
            self.session.add(
                SchemeDocument(
                    scheme_id=scheme_id,
                    document_name=doc.name,
                    is_required=doc.required,
                    display_order=order,
                )
            )
        await self.session.flush()

    # ----------------------------------------------------------------- #
    # Reads
    # ----------------------------------------------------------------- #
    async def get(self, scheme_id: uuid.UUID) -> GovernmentScheme | None:
        result = await self.session.execute(
            select(GovernmentScheme).where(
                GovernmentScheme.id == scheme_id,
                GovernmentScheme.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def list_active(self) -> list[GovernmentScheme]:
        """All active schemes — the engine evaluates every one for a farmer."""
        result = await self.session.execute(
            select(GovernmentScheme).where(
                GovernmentScheme.is_deleted.is_(False),
                GovernmentScheme.status == SchemeStatus.ACTIVE.value,
            )
        )
        return list(result.scalars().all())

    def _filtered(
        self,
        *,
        category: str | None,
        state: str | None,
        crop: str | None,
        search: str | None,
    ) -> Select[tuple[GovernmentScheme]]:
        stmt = select(GovernmentScheme).where(GovernmentScheme.is_deleted.is_(False))
        if category:
            stmt = stmt.where(GovernmentScheme.category == category)
        if state:
            stmt = stmt.where(
                or_(
                    func.lower(GovernmentScheme.state) == state.lower(),
                    func.lower(GovernmentScheme.state) == "all",
                )
            )
        if crop:
            # Crop filter is a client convenience over the free-text search.
            stmt = stmt.where(
                or_(
                    func.lower(GovernmentScheme.title).like(f"%{crop.lower()}%"),
                    func.lower(GovernmentScheme.description).like(f"%{crop.lower()}%"),
                )
            )
        if search:
            like = f"%{search.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(GovernmentScheme.title).like(like),
                    func.lower(GovernmentScheme.description).like(like),
                )
            )
        return stmt

    async def list_schemes(
        self,
        *,
        category: str | None = None,
        state: str | None = None,
        crop: str | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[GovernmentScheme], int]:
        base = self._filtered(
            category=category, state=state, crop=crop, search=search
        )
        total = int(
            (
                await self.session.execute(
                    select(func.count()).select_from(base.subquery())
                )
            ).scalar_one()
        )
        rows = (
            await self.session.execute(
                base.order_by(GovernmentScheme.title.asc()).limit(limit).offset(offset)
            )
        ).scalars().all()
        return list(rows), total

    async def schemes_by_ids(
        self, ids: list[uuid.UUID]
    ) -> list[GovernmentScheme]:
        if not ids:
            return []
        result = await self.session.execute(
            select(GovernmentScheme).where(
                GovernmentScheme.id.in_(ids),
                GovernmentScheme.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())

    # ----------------------------------------------------------------- #
    # Documents
    # ----------------------------------------------------------------- #
    async def documents_for(self, scheme_id: uuid.UUID) -> list[SchemeDocument]:
        result = await self.session.execute(
            select(SchemeDocument)
            .where(SchemeDocument.scheme_id == scheme_id)
            .order_by(SchemeDocument.display_order.asc())
        )
        return list(result.scalars().all())

    # ----------------------------------------------------------------- #
    # Bookmarks (user-scoped)
    # ----------------------------------------------------------------- #
    async def list_bookmarks(self, user_id: uuid.UUID) -> list[SchemeBookmark]:
        result = await self.session.execute(
            select(SchemeBookmark)
            .where(
                SchemeBookmark.user_id == user_id,
                SchemeBookmark.is_deleted.is_(False),
            )
            .order_by(SchemeBookmark.created_at.desc())
        )
        return list(result.scalars().all())

    async def bookmarked_ids(self, user_id: uuid.UUID) -> set[uuid.UUID]:
        result = await self.session.execute(
            select(SchemeBookmark.scheme_id).where(
                SchemeBookmark.user_id == user_id,
                SchemeBookmark.is_deleted.is_(False),
            )
        )
        return set(result.scalars().all())

    async def get_bookmark(
        self, user_id: uuid.UUID, scheme_id: uuid.UUID
    ) -> SchemeBookmark | None:
        result = await self.session.execute(
            select(SchemeBookmark).where(
                SchemeBookmark.user_id == user_id,
                SchemeBookmark.scheme_id == scheme_id,
                SchemeBookmark.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def add_bookmark(self, bookmark: SchemeBookmark) -> SchemeBookmark:
        self.session.add(bookmark)
        await self.session.flush()
        return bookmark

    async def soft_delete_bookmark(self, bookmark: SchemeBookmark) -> None:
        bookmark.is_deleted = True
        await self.session.flush()
