"""Scheme service (docs: Repository → Service → Eligibility Engine → Provider).

Seeds verified schemes from the provider, builds the farmer's context from their
profile + farm(s), runs the deterministic eligibility engine and returns eligible
schemes ranked by score. Business logic lives here; routes stay thin.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.timezone import today_ist
from app.modules.auth.models import User
from app.modules.auth.repositories import FarmerProfileRepository
from app.modules.farms.repositories import FarmRepository
from app.modules.schemes.constants import (
    RECOMMENDED_MIN_COUNT,
    RECOMMENDED_SCORE_THRESHOLD,
    DocumentType,
    derive_farmer_category,
)
from app.modules.schemes.engine import (
    EligibilityResult,
    FarmerContext,
    SchemeRules,
    evaluate,
    is_eligible,
    rank,
)
from app.modules.schemes.exceptions import (
    BookmarkExistsError,
    BookmarkNotFoundError,
    SchemeNotFoundError,
)
from app.modules.schemes.models import GovernmentScheme, SchemeBookmark
from app.modules.schemes.provider import GovernmentSchemeProvider, get_default_provider
from app.modules.schemes.repository import SchemeRepository
from app.modules.schemes.schemas import (
    EligibilityQuery,
    FarmerDocumentOut,
    SchemeDetailOut,
    SchemePageMeta,
    SchemeSummaryOut,
)
from app.schemas.response import PaginatedData

logger = get_logger("schemes.service")

# The app is Tamil-Nadu-first (Tamil-first UI, TN districts); when the farmer's
# state is unknown we assume Tamil Nadu so state-specific TN schemes evaluate.
DEFAULT_STATE = "Tamil Nadu"


class SchemeService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        provider: GovernmentSchemeProvider | None = None,
    ) -> None:
        self.session = session
        self.repo = SchemeRepository(session)
        self.profiles = FarmerProfileRepository(session)
        self.farms = FarmRepository(session)
        self.provider = provider or get_default_provider()

    # ----------------------------------------------------------------- #
    # Seeding
    # ----------------------------------------------------------------- #
    async def ensure_seeded(self) -> None:
        """Populate verified schemes from the provider once (idempotent)."""
        if await self.repo.count() > 0:
            return
        schemes = await self.provider.fetch_schemes()
        for record in schemes:
            await self.repo.upsert_scheme(record)
        logger.info("seeded %s verified schemes", len(schemes))

    # ----------------------------------------------------------------- #
    # Farmer context
    # ----------------------------------------------------------------- #
    async def build_context(
        self, user: User, query: EligibilityQuery | None
    ) -> FarmerContext:
        query = query or EligibilityQuery()
        profile = await self.profiles.get_by_user_id(user.id)

        land = query.land_hectares
        crop = query.crop
        district = query.district
        annual_income = query.annual_income

        farm = None
        if query.farm_id is not None:
            farm = await self.farms.get_for_user(query.farm_id, user.id)
        if farm is not None:
            land = land if land is not None else farm.area_hectares
            crop = crop or farm.crop
            district = district or (farm.location.district if farm.location else None)
        elif land is None:
            # No specific farm → total operational holding across the farmer's farms.
            farms = await self.farms.list_for_user(user.id, limit=100, offset=0)
            total = sum(f.area_hectares or 0 for f in farms)
            land = total or None
            if crop is None:
                crop = next((f.crop for f in farms if f.crop), None)
            if district is None:
                district = next(
                    (f.location.district for f in farms if f.location and f.location.district),
                    None,
                )

        if profile is not None:
            district = district or profile.district
            crop = crop or profile.primary_crop
            annual_income = (
                annual_income if annual_income is not None else profile.annual_income
            )

        category = query.farmer_category or derive_farmer_category(land)
        return FarmerContext(
            state=query.state or DEFAULT_STATE,
            district=district,
            crop=crop,
            land_hectares=land,
            annual_income=annual_income,
            farmer_category=category,
        )

    @staticmethod
    def context_meta(context: FarmerContext) -> SchemePageMeta:
        return SchemePageMeta(
            district=context.district,
            crop=context.crop,
            land_hectares=context.land_hectares,
            farmer_category=(
                context.farmer_category.value if context.farmer_category else None
            ),
        )

    # ----------------------------------------------------------------- #
    # Listing
    # ----------------------------------------------------------------- #
    async def list_all(
        self,
        user: User,
        *,
        category: str | None,
        state: str | None,
        crop: str | None,
        search: str | None,
        page: int,
        page_size: int,
    ) -> PaginatedData[SchemeSummaryOut]:
        await self.ensure_seeded()
        offset = (page - 1) * page_size
        rows, total = await self.repo.list_schemes(
            category=category,
            state=state,
            crop=crop,
            search=search,
            limit=page_size,
            offset=offset,
        )
        bookmarked = await self.repo.bookmarked_ids(user.id)
        items = [
            SchemeSummaryOut.from_scheme(s, bookmarked=s.id in bookmarked)
            for s in rows
        ]
        total_pages = (total + page_size - 1) // page_size if total else 0
        return PaginatedData(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )

    async def get_detail(
        self, user: User, scheme_id: uuid.UUID, query: EligibilityQuery | None = None
    ) -> SchemeDetailOut:
        await self.ensure_seeded()
        scheme = await self.repo.get(scheme_id)
        if scheme is None:
            raise SchemeNotFoundError()
        documents = await self.repo.documents_for(scheme.id)
        farmer_documents = await self.repo.farmer_documents(user.id)
        owned_documents = {
            row.document_type for row in farmer_documents if row.has_document
        }
        bookmarked = await self.repo.get_bookmark(user.id, scheme.id) is not None
        context = await self.build_context(user, query)
        result = evaluate(SchemeRules.from_scheme(scheme), context, today=today_ist())
        return SchemeDetailOut.from_detail(
            scheme,
            documents=documents,
            owned_documents=owned_documents,
            bookmarked=bookmarked,
            eligibility=result,
        )

    async def list_farmer_documents(self, user: User) -> list[FarmerDocumentOut]:
        rows = await self.repo.farmer_documents(user.id)
        values = {row.document_type: row.has_document for row in rows}
        return [
            FarmerDocumentOut(
                document_type=document_type,
                has_document=values.get(document_type.value, False),
            )
            for document_type in DocumentType
        ]

    async def set_farmer_document(
        self, user: User, document_type: DocumentType, has_document: bool
    ) -> FarmerDocumentOut:
        row = await self.repo.set_farmer_document(
            user.id, document_type.value, has_document
        )
        return FarmerDocumentOut(
            document_type=DocumentType(row.document_type),
            has_document=row.has_document,
        )

    # ----------------------------------------------------------------- #
    # Eligibility engine driven
    # ----------------------------------------------------------------- #
    async def _evaluate_all(
        self, user: User, context: FarmerContext
    ) -> list[tuple[GovernmentScheme, EligibilityResult]]:
        schemes = await self.repo.list_active()
        today = today_ist()
        return [
            (s, evaluate(SchemeRules.from_scheme(s), context, today=today))
            for s in schemes
        ]

    async def eligible(
        self,
        user: User,
        query: EligibilityQuery | None,
        *,
        page: int,
        page_size: int,
    ) -> tuple[PaginatedData[SchemeSummaryOut], SchemePageMeta]:
        await self.ensure_seeded()
        context = await self.build_context(user, query)
        evaluated = [
            (s, r) for s, r in await self._evaluate_all(user, context) if is_eligible(r)
        ]
        ranked = rank(evaluated)
        bookmarked = await self.repo.bookmarked_ids(user.id)

        total = len(ranked)
        start = (page - 1) * page_size
        page_rows = ranked[start : start + page_size]
        items = [
            SchemeSummaryOut.from_scheme(
                s, bookmarked=s.id in bookmarked, eligibility=r
            )
            for s, r in page_rows
        ]
        total_pages = (total + page_size - 1) // page_size if total else 0
        data = PaginatedData(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )
        return data, self.context_meta(context)

    async def recommended(
        self, user: User, query: EligibilityQuery | None
    ) -> tuple[list[SchemeSummaryOut], SchemePageMeta]:
        await self.ensure_seeded()
        context = await self.build_context(user, query)
        evaluated = [
            (s, r) for s, r in await self._evaluate_all(user, context) if is_eligible(r)
        ]
        ranked = rank(evaluated)
        # Recommend high-scoring eligible schemes; always surface a minimum set.
        strong = [(s, r) for s, r in ranked if r.score >= RECOMMENDED_SCORE_THRESHOLD]
        chosen = strong if len(strong) >= RECOMMENDED_MIN_COUNT else ranked[
            :RECOMMENDED_MIN_COUNT
        ]
        bookmarked = await self.repo.bookmarked_ids(user.id)
        items = [
            SchemeSummaryOut.from_scheme(
                s, bookmarked=s.id in bookmarked, eligibility=r
            )
            for s, r in chosen
        ]
        return items, self.context_meta(context)

    # ----------------------------------------------------------------- #
    # Bookmarks
    # ----------------------------------------------------------------- #
    async def list_bookmarks(
        self, user: User, query: EligibilityQuery | None = None
    ) -> list[SchemeSummaryOut]:
        await self.ensure_seeded()
        bookmarks = await self.repo.list_bookmarks(user.id)
        ids = [b.scheme_id for b in bookmarks]
        schemes = {s.id: s for s in await self.repo.schemes_by_ids(ids)}
        context = await self.build_context(user, query)
        ordered = [schemes[i] for i in ids if i in schemes]
        return [
            SchemeSummaryOut.from_scheme(
                s,
                bookmarked=True,
                eligibility=evaluate(
                    SchemeRules.from_scheme(s), context, today=today_ist()
                ),
            )
            for s in ordered
        ]

    async def add_bookmark(self, user: User, scheme_id: uuid.UUID) -> None:
        await self.ensure_seeded()
        scheme = await self.repo.get(scheme_id)
        if scheme is None:
            raise SchemeNotFoundError()
        if await self.repo.get_bookmark(user.id, scheme_id) is not None:
            raise BookmarkExistsError()
        await self.repo.add_bookmark(
            SchemeBookmark(user_id=user.id, scheme_id=scheme_id)
        )

    async def remove_bookmark(self, user: User, scheme_id: uuid.UUID) -> None:
        bookmark = await self.repo.get_bookmark(user.id, scheme_id)
        if bookmark is None:
            raise BookmarkNotFoundError()
        await self.repo.soft_delete_bookmark(bookmark)
