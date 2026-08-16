"""Produce service (docs: Repository → Service → Procurement Engine → Provider).

Validates and persists verified future-harvest offers, freezes a verified market
-price snapshot (reused from the Market module — never fabricated), runs the
deterministic Procurement Engine to enrich each offer, routes submissions through
the injectable ``ProduceProvider`` and tracks the lifecycle. Business logic lives
here; routes stay thin.
"""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.timezone import today_ist
from app.modules.auth.models import User
from app.modules.farms.repositories import FarmRepository
from app.modules.market.repository import MarketRepository
from app.modules.produce.constants import (
    FARMER_SETTABLE_STATUSES,
    ProcurementChannel,
    ProduceStatus,
)
from app.modules.produce.engine import (
    OfferFacts,
    PriceReference,
    ProcurementInsight,
    compute_insight,
)
from app.modules.produce.exceptions import (
    FarmNotOwnedError,
    InvalidProduceError,
    InvalidStatusTransitionError,
    ProduceOfferNotFoundError,
)
from app.modules.produce.models import (
    OfferImage,
    OfferStatusHistory,
    ProduceOffer,
)
from app.modules.produce.provider import OfferRef, ProduceProvider, get_default_provider
from app.modules.produce.repository import ProduceRepository
from app.modules.produce.schemas import (
    ProduceImageIn,
    ProduceListFilters,
    ProduceOfferCreate,
    ProduceOfferUpdate,
)
from app.schemas.response import PaginatedData

logger = get_logger("produce.service")


class ProduceService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        provider: ProduceProvider | None = None,
        today: date | None = None,
    ) -> None:
        self.session = session
        self.repo = ProduceRepository(session)
        self.farms = FarmRepository(session)
        self.market = MarketRepository(session)
        self.provider = provider or get_default_provider()
        self._today = today

    def _now_date(self) -> date:
        # India Standard Time, not UTC (docs: app.core.timezone) -- this is a
        # "what day is it for the farmer" boundary, not an event timestamp.
        return self._today or today_ist()

    # ----------------------------------------------------------------- #
    # Validation
    # ----------------------------------------------------------------- #
    def _validate_harvest_date(self, harvest_date: date) -> None:
        if harvest_date < self._now_date():
            raise InvalidProduceError("Expected harvest date cannot be in the past.")

    async def _require_farm(self, user: User, farm_id: uuid.UUID):
        farm = await self.farms.get_for_user(farm_id, user.id)
        if farm is None:
            raise FarmNotOwnedError()
        return farm

    async def _require_offer(self, user: User, offer_id: uuid.UUID) -> ProduceOffer:
        offer = await self.repo.get_for_user(offer_id, user.id)
        if offer is None:
            raise ProduceOfferNotFoundError()
        return offer

    # ----------------------------------------------------------------- #
    # Verified market-price snapshot (reused from Market — never fabricated)
    # ----------------------------------------------------------------- #
    async def _fetch_price_reference(
        self, crop: str, district: str | None
    ) -> PriceReference | None:
        rows, _ = await self.market.list_prices(
            crop=crop, district=district, limit=1, offset=0
        )
        if not rows:
            # Retry without the district constraint (still verified data).
            rows, _ = await self.market.list_prices(crop=crop, limit=1, offset=0)
        if not rows:
            return None
        price, location = rows[0]
        return PriceReference(
            modal_price=price.modal_price,
            minimum_price=price.minimum_price,
            maximum_price=price.maximum_price,
            unit=price.unit,
            source=price.source,
            price_date=price.price_date,
            market=location.market_name,
            district=location.district,
        )

    @staticmethod
    def _reference_from_snapshot(offer: ProduceOffer) -> PriceReference | None:
        """Rebuild the frozen snapshot for reads (no re-query, stays faithful)."""
        if offer.current_market_price_snapshot is None or offer.market_price_unit is None:
            return None
        return PriceReference(
            modal_price=offer.current_market_price_snapshot,
            minimum_price=offer.market_price_min
            if offer.market_price_min is not None
            else offer.current_market_price_snapshot,
            maximum_price=offer.market_price_max
            if offer.market_price_max is not None
            else offer.current_market_price_snapshot,
            unit=offer.market_price_unit,
            source=offer.market_price_source or "market",
            price_date=offer.market_price_date or offer.expected_harvest_date,
            district=offer.district,
        )

    def _insight(self, offer: ProduceOffer) -> ProcurementInsight:
        return compute_insight(
            OfferFacts(
                quantity=offer.quantity,
                unit=offer.unit,
                expected_harvest_date=offer.expected_harvest_date,
                asking_price=offer.asking_price,
            ),
            self._reference_from_snapshot(offer),
            today=self._now_date(),
        )

    def _apply_snapshot(self, offer: ProduceOffer, ref: PriceReference | None) -> None:
        if ref is None:
            offer.current_market_price_snapshot = None
            offer.market_price_min = None
            offer.market_price_max = None
            offer.market_price_unit = None
            offer.market_price_source = None
            offer.market_price_date = None
            return
        offer.current_market_price_snapshot = ref.modal_price
        offer.market_price_min = ref.minimum_price
        offer.market_price_max = ref.maximum_price
        offer.market_price_unit = ref.unit
        offer.market_price_source = ref.source
        offer.market_price_date = ref.price_date

    async def _record_status(
        self,
        offer: ProduceOffer,
        *,
        old: str | None,
        new: str,
        by: uuid.UUID | None,
        note: str | None = None,
    ) -> None:
        await self.repo.add_status_history(
            OfferStatusHistory(
                offer_id=offer.id, old_status=old, new_status=new, changed_by=by, note=note
            )
        )

    # ----------------------------------------------------------------- #
    # Create
    # ----------------------------------------------------------------- #
    async def create_offer(self, user: User, data: ProduceOfferCreate) -> ProduceOffer:
        self._validate_harvest_date(data.expected_harvest_date)
        farm = await self._require_farm(user, data.farm_id)

        district = data.district or (farm.location.district if farm.location else None)
        block = data.block or (farm.location.block if farm.location else None)
        village = data.village or (farm.location.village if farm.location else None)
        latitude = data.latitude if data.latitude is not None else (
            farm.location.latitude if farm.location else None
        )
        longitude = data.longitude if data.longitude is not None else (
            farm.location.longitude if farm.location else None
        )

        offer = ProduceOffer(
            user_id=user.id,
            farm_id=farm.id,
            crop_name=data.crop_name,
            variety=data.variety,
            quantity=data.quantity,
            unit=data.unit.value,
            expected_harvest_date=data.expected_harvest_date,
            expected_grade=data.expected_grade.value if data.expected_grade else None,
            asking_price=data.asking_price,
            currency=data.currency,
            available_from=data.available_from,
            available_until=data.available_until,
            district=district,
            block=block,
            village=village,
            latitude=latitude,
            longitude=longitude,
            notes=data.notes,
            status=data.status.value,
        )

        # Freeze a verified market-price snapshot (never fabricated).
        reference = await self._fetch_price_reference(data.crop_name, district)
        self._apply_snapshot(offer, reference)

        await self.repo.add(offer)

        for index, image in enumerate(data.images):
            await self._attach_image(user, offer, image, order=index)

        await self._record_status(
            offer, old=None, new=offer.status, by=user.id, note="Offer created"
        )

        # Route a submitted offer to the procurement channel (mock in V1).
        if offer.status == ProduceStatus.SUBMITTED.value:
            await self._submit_to_provider(offer)

        await self.session.flush()
        return offer

    async def _submit_to_provider(self, offer: ProduceOffer) -> None:
        ack = await self.provider.submit(
            OfferRef(
                id=str(offer.id),
                crop_name=offer.crop_name,
                quantity=offer.quantity,
                unit=offer.unit,
                district=offer.district,
            )
        )
        if ack is None:
            offer.procurement_channel = None
            offer.procurement_reference = None
            return
        offer.procurement_channel = ack.channel
        offer.procurement_reference = ack.reference

    async def _attach_image(
        self, user: User, offer: ProduceOffer, image: ProduceImageIn, *, order: int
    ) -> OfferImage:
        entity = OfferImage(
            offer_id=offer.id,
            user_id=user.id,
            image_url=image.image_url,
            thumbnail_url=image.thumbnail_url,
            mime_type=image.mime_type,
            file_size=image.file_size,
            caption=image.caption,
            display_order=order,
        )
        return await self.repo.add_image(entity)

    # ----------------------------------------------------------------- #
    # Reads
    # ----------------------------------------------------------------- #
    async def list_offers(
        self, user: User, filters: ProduceListFilters
    ) -> tuple[PaginatedData[ProduceOffer], dict[uuid.UUID, ProcurementInsight]]:
        offset = (filters.page - 1) * filters.page_size
        rows, total = await self.repo.list_for_user(
            user.id,
            status=filters.status.value if filters.status else None,
            crop=filters.crop,
            farm_id=filters.farm_id,
            search=filters.search,
            limit=filters.page_size,
            offset=offset,
        )
        insights = {o.id: self._insight(o) for o in rows}
        total_pages = (total + filters.page_size - 1) // filters.page_size if total else 0
        page = PaginatedData(
            items=rows,
            page=filters.page,
            page_size=filters.page_size,
            total=total,
            total_pages=total_pages,
        )
        return page, insights

    async def get_offer(
        self, user: User, offer_id: uuid.UUID
    ) -> tuple[ProduceOffer, ProcurementInsight]:
        offer = await self._require_offer(user, offer_id)
        return offer, self._insight(offer)

    async def _paginated_by_statuses(
        self,
        user: User,
        *,
        statuses: tuple[str, ...],
        page: int,
        page_size: int,
        harvest_from: date | None,
        order_by_harvest: bool,
    ) -> tuple[PaginatedData[ProduceOffer], dict[uuid.UUID, ProcurementInsight]]:
        offset = (page - 1) * page_size
        rows, total = await self.repo.list_for_user(
            user.id,
            statuses=statuses,
            harvest_from=harvest_from,
            order_by_harvest=order_by_harvest,
            limit=page_size,
            offset=offset,
        )
        insights = {o.id: self._insight(o) for o in rows}
        total_pages = (total + page_size - 1) // page_size if total else 0
        return (
            PaginatedData(
                items=rows,
                page=page,
                page_size=page_size,
                total=total,
                total_pages=total_pages,
            ),
            insights,
        )

    async def upcoming(
        self, user: User, *, page: int, page_size: int
    ) -> tuple[PaginatedData[ProduceOffer], dict[uuid.UUID, ProcurementInsight]]:
        """Still-relevant harvests due today or later, soonest first."""
        return await self._paginated_by_statuses(
            user,
            statuses=await self.repo.upcoming_statuses(),
            page=page,
            page_size=page_size,
            harvest_from=self._now_date(),
            order_by_harvest=True,
        )

    async def history(
        self, user: User, *, page: int, page_size: int
    ) -> tuple[PaginatedData[ProduceOffer], dict[uuid.UUID, ProcurementInsight]]:
        """Concluded offers (harvested / fulfilled / withdrawn / expired)."""
        return await self._paginated_by_statuses(
            user,
            statuses=await self.repo.history_statuses(),
            page=page,
            page_size=page_size,
            harvest_from=None,
            order_by_harvest=False,
        )

    # ----------------------------------------------------------------- #
    # Update / delete
    # ----------------------------------------------------------------- #
    async def update_offer(
        self, user: User, offer_id: uuid.UUID, data: ProduceOfferUpdate
    ) -> tuple[ProduceOffer, ProcurementInsight]:
        offer = await self._require_offer(user, offer_id)
        fields = data.model_dump(exclude_unset=True)

        if "expected_harvest_date" in fields and fields["expected_harvest_date"]:
            self._validate_harvest_date(fields["expected_harvest_date"])

        status_change = fields.pop("status", None)
        crop_or_district_changed = False

        for key, value in fields.items():
            if key in {"unit", "expected_grade"} and value is not None:
                value = value.value if hasattr(value, "value") else value
            if key in {"crop_name", "district"} and value != getattr(offer, key):
                crop_or_district_changed = True
            setattr(offer, key, value)

        # Re-freeze the verified snapshot only if the crop or district changed.
        if crop_or_district_changed:
            reference = await self._fetch_price_reference(offer.crop_name, offer.district)
            self._apply_snapshot(offer, reference)

        if status_change is not None:
            await self._change_status(user, offer, status_change.value)

        await self.session.flush()
        await self.session.refresh(offer)
        return offer, self._insight(offer)

    async def _change_status(self, user: User, offer: ProduceOffer, new: str) -> None:
        if new == offer.status:
            return
        if new not in FARMER_SETTABLE_STATUSES:
            raise InvalidStatusTransitionError(
                f"'{new}' is not a status a farmer can set."
            )
        old = offer.status
        offer.status = new
        await self._record_status(offer, old=old, new=new, by=user.id)
        # Submitting via an edit also routes to the procurement channel.
        if new == ProduceStatus.SUBMITTED.value and offer.procurement_reference is None:
            await self._submit_to_provider(offer)

    async def delete_offer(self, user: User, offer_id: uuid.UUID) -> None:
        offer = await self._require_offer(user, offer_id)
        await self.repo.soft_delete(offer)

    # ----------------------------------------------------------------- #
    # Images
    # ----------------------------------------------------------------- #
    async def add_image(
        self, user: User, offer_id: uuid.UUID, image: ProduceImageIn
    ) -> tuple[ProduceOffer, OfferImage]:
        offer = await self._require_offer(user, offer_id)
        order = await self.repo.next_image_order(offer.id)
        entity = await self._attach_image(user, offer, image, order=order)
        await self.session.flush()
        await self.session.refresh(offer)
        return offer, entity

    # ----------------------------------------------------------------- #
    # Future-ready buyer interest (reads only; never fabricated in V1)
    # ----------------------------------------------------------------- #
    async def buyer_interest(self, user: User, offer_id: uuid.UUID):
        await self._require_offer(user, offer_id)
        return await self.repo.list_buyer_interest(offer_id)

    @staticmethod
    def default_channel() -> str:
        return ProcurementChannel.MOCK.value
