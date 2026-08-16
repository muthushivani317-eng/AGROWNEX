"""Produce repository (docs/BACKEND_ARCHITECTURE.md → Repository Pattern).

The only layer that queries the produce tables: offers (ownership-scoped, filtered,
paginated), images, status history and the future-ready buyer_interest table. No
SQL lives in routes or the service.
"""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.produce.constants import ProduceStatus
from app.modules.produce.models import (
    BuyerInterest,
    OfferImage,
    OfferStatusHistory,
    ProduceOffer,
)

# Statuses that represent a still-relevant, upcoming harvest.
_UPCOMING_STATUSES = (
    ProduceStatus.SUBMITTED.value,
    ProduceStatus.PLANNED.value,
)
# Statuses that represent a concluded lifecycle (history view).
_HISTORY_STATUSES = (
    ProduceStatus.HARVESTED.value,
    ProduceStatus.FULFILLED.value,
    ProduceStatus.WITHDRAWN.value,
    ProduceStatus.EXPIRED.value,
)
# Still-open statuses that can go stale and need to age into EXPIRED
# (docs: app.modules.produce.jobs.expire_stale_offers).
_EXPIRABLE_STATUSES = (
    ProduceStatus.DRAFT.value,
    ProduceStatus.SUBMITTED.value,
    ProduceStatus.PLANNED.value,
)


class ProduceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ----------------------------------------------------------------- #
    # Offers
    # ----------------------------------------------------------------- #
    def _owned(self, user_id: uuid.UUID) -> Select[tuple[ProduceOffer]]:
        return select(ProduceOffer).where(
            ProduceOffer.user_id == user_id,
            ProduceOffer.is_deleted.is_(False),
        )

    async def add(self, offer: ProduceOffer) -> ProduceOffer:
        self.session.add(offer)
        await self.session.flush()
        return offer

    async def get_for_user(
        self, offer_id: uuid.UUID, user_id: uuid.UUID
    ) -> ProduceOffer | None:
        result = await self.session.execute(
            self._owned(user_id).where(ProduceOffer.id == offer_id)
        )
        return result.scalar_one_or_none()

    def _filtered(
        self,
        user_id: uuid.UUID,
        *,
        status: str | None,
        crop: str | None,
        farm_id: uuid.UUID | None,
        statuses: tuple[str, ...] | None,
        harvest_from: date | None,
        search: str | None,
    ) -> Select[tuple[ProduceOffer]]:
        stmt = self._owned(user_id)
        if status:
            stmt = stmt.where(ProduceOffer.status == status)
        if statuses:
            stmt = stmt.where(ProduceOffer.status.in_(statuses))
        if crop:
            stmt = stmt.where(func.lower(ProduceOffer.crop_name).like(f"%{crop.lower()}%"))
        if farm_id:
            stmt = stmt.where(ProduceOffer.farm_id == farm_id)
        if harvest_from is not None:
            stmt = stmt.where(ProduceOffer.expected_harvest_date >= harvest_from)
        if search:
            like = f"%{search.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(ProduceOffer.crop_name).like(like),
                    func.lower(ProduceOffer.variety).like(like),
                )
            )
        return stmt

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        status: str | None = None,
        crop: str | None = None,
        farm_id: uuid.UUID | None = None,
        statuses: tuple[str, ...] | None = None,
        harvest_from: date | None = None,
        search: str | None = None,
        order_by_harvest: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ProduceOffer], int]:
        base = self._filtered(
            user_id,
            status=status,
            crop=crop,
            farm_id=farm_id,
            statuses=statuses,
            harvest_from=harvest_from,
            search=search,
        )
        total = int(
            (
                await self.session.execute(
                    select(func.count()).select_from(base.subquery())
                )
            ).scalar_one()
        )
        ordering = (
            ProduceOffer.expected_harvest_date.asc()
            if order_by_harvest
            else ProduceOffer.created_at.desc()
        )
        rows = (
            await self.session.execute(base.order_by(ordering).limit(limit).offset(offset))
        ).scalars().unique().all()
        return list(rows), total

    async def upcoming_statuses(self) -> tuple[str, ...]:
        return _UPCOMING_STATUSES

    async def history_statuses(self) -> tuple[str, ...]:
        return _HISTORY_STATUSES

    async def soft_delete(self, offer: ProduceOffer) -> None:
        offer.is_deleted = True
        await self.session.flush()

    async def list_stale_open_offers(self, *, cutoff: date) -> list[ProduceOffer]:
        """Still-open offers whose expected harvest date is before ``cutoff``.

        Used by the expiry job to find offers a farmer never acted on (never
        marked harvested/withdrawn) well past their own stated harvest date.
        """
        result = await self.session.execute(
            select(ProduceOffer).where(
                ProduceOffer.is_deleted.is_(False),
                ProduceOffer.status.in_(_EXPIRABLE_STATUSES),
                ProduceOffer.expected_harvest_date < cutoff,
            )
        )
        return list(result.scalars().all())

    # ----------------------------------------------------------------- #
    # Images
    # ----------------------------------------------------------------- #
    async def add_image(self, image: OfferImage) -> OfferImage:
        self.session.add(image)
        await self.session.flush()
        return image

    async def next_image_order(self, offer_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(OfferImage).where(
                OfferImage.offer_id == offer_id
            )
        )
        return int(result.scalar_one())

    async def list_images(self, offer_id: uuid.UUID) -> list[OfferImage]:
        result = await self.session.execute(
            select(OfferImage)
            .where(OfferImage.offer_id == offer_id)
            .order_by(OfferImage.display_order.asc())
        )
        return list(result.scalars().all())

    # ----------------------------------------------------------------- #
    # Status history
    # ----------------------------------------------------------------- #
    async def add_status_history(self, entry: OfferStatusHistory) -> OfferStatusHistory:
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def list_status_history(
        self, offer_id: uuid.UUID
    ) -> list[OfferStatusHistory]:
        result = await self.session.execute(
            select(OfferStatusHistory)
            .where(OfferStatusHistory.offer_id == offer_id)
            .order_by(OfferStatusHistory.created_at.asc())
        )
        return list(result.scalars().all())

    # ----------------------------------------------------------------- #
    # Buyer interest (future-ready)
    # ----------------------------------------------------------------- #
    async def list_buyer_interest(self, offer_id: uuid.UUID) -> list[BuyerInterest]:
        result = await self.session.execute(
            select(BuyerInterest).where(
                BuyerInterest.offer_id == offer_id,
                BuyerInterest.is_deleted.is_(False),
            )
        )
        return list(result.scalars().all())

    async def add_buyer_interest(self, interest: BuyerInterest) -> BuyerInterest:
        self.session.add(interest)
        await self.session.flush()
        return interest
