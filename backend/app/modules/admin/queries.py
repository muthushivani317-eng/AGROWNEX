"""Admin cross-module read queries — farmer management + procurement (read-only).

Kept separate from ``metrics.py`` (aggregates) so each file stays small
(docs/CODING_STANDARDS.md). Every query is read-only; farmer data is never modified.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.admin.metrics import FarmerRow, ProcurementRow


class AdminQueries:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ----------------------------------------------------------------- #
    # Farmer management
    # ----------------------------------------------------------------- #
    async def farmers(
        self,
        *,
        search: str | None = None,
        district: str | None = None,
        crop: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[FarmerRow], int]:
        from app.modules.auth.models import User
        from app.modules.auth.profile_models import FarmerProfile

        base = (
            select(FarmerProfile, User)
            .join(User, User.id == FarmerProfile.user_id)
            .where(FarmerProfile.is_deleted.is_(False), User.deleted_at.is_(None))
        )
        if district:
            base = base.where(FarmerProfile.district == district)
        if crop:
            base = base.where(FarmerProfile.primary_crop == crop)
        if search:
            like = f"%{search.lower()}%"
            base = base.where(
                or_(
                    func.lower(FarmerProfile.full_name).like(like),
                    func.lower(FarmerProfile.village).like(like),
                    User.phone_number.like(f"%{search}%"),
                    func.lower(User.farmer_ref).like(like),
                )
            )

        total = int(
            (
                await self.session.execute(select(func.count()).select_from(base.subquery()))
            ).scalar_one()
        )
        rows = (
            await self.session.execute(
                base.order_by(FarmerProfile.created_at.desc()).limit(limit).offset(offset)
            )
        ).all()

        user_ids = [profile.user_id for profile, _user in rows]
        farm_counts = await self._farm_counts(user_ids)

        farmers = [
            FarmerRow(
                user_id=profile.user_id,
                farmer_ref=user.farmer_ref,
                full_name=profile.full_name,
                phone_number=user.phone_number,
                district=profile.district,
                village=profile.village,
                primary_crop=profile.primary_crop,
                language=profile.language,
                farm_count=farm_counts.get(profile.user_id, 0),
                created_at=profile.created_at,
            )
            for profile, user in rows
        ]
        return farmers, total

    async def _farm_counts(self, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
        from app.modules.farms.models import Farm

        if not user_ids:
            return {}
        rows = (
            await self.session.execute(
                select(Farm.user_id, func.count())
                .where(Farm.user_id.in_(user_ids), Farm.is_deleted.is_(False))
                .group_by(Farm.user_id)
            )
        ).all()
        return {uid: int(count) for uid, count in rows}

    async def farmer_detail(self, user_id: uuid.UUID) -> dict | None:
        from app.modules.ai.models import AIConversation
        from app.modules.auth.models import User
        from app.modules.auth.profile_models import FarmerProfile
        from app.modules.disease.models import DiseaseReport
        from app.modules.farms.models import Farm
        from app.modules.memory.models import FarmMemory
        from app.modules.notifications.models import Notification
        from app.modules.soil.models import SoilReport

        profile = (
            await self.session.execute(
                select(FarmerProfile).where(FarmerProfile.user_id == user_id)
            )
        ).scalar_one_or_none()
        user = (
            await self.session.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none()
        if profile is None and user is None:
            return None

        farms = (
            (
                await self.session.execute(
                    select(Farm)
                    .where(Farm.user_id == user_id, Farm.is_deleted.is_(False))
                    .order_by(Farm.created_at.desc())
                )
            )
            .scalars()
            .all()
        )

        async def _count(stmt) -> int:  # noqa: ANN001
            return int(
                (
                    await self.session.execute(select(func.count()).select_from(stmt.subquery()))
                ).scalar_one()
            )

        counts = {
            "disease": await _count(select(DiseaseReport).where(DiseaseReport.user_id == user_id)),
            "soil": await _count(
                select(SoilReport).where(
                    SoilReport.user_id == user_id, SoilReport.is_deleted.is_(False)
                )
            ),
            "ai_chats": await _count(
                select(AIConversation).where(AIConversation.user_id == user_id)
            ),
            "memory": await _count(
                select(FarmMemory).where(
                    FarmMemory.user_id == user_id, FarmMemory.is_deleted.is_(False)
                )
            ),
            "notifications": await _count(
                select(Notification).where(Notification.user_id == user_id)
            ),
        }
        return {"profile": profile, "user": user, "farms": list(farms), "counts": counts}

    # ----------------------------------------------------------------- #
    # Procurement
    # ----------------------------------------------------------------- #
    async def procurement_offers(
        self,
        *,
        crop: str | None = None,
        village: str | None = None,
        district: str | None = None,
        search: str | None = None,
        category: str | None = None,
        availability_type: str | None = None,
        organic_only: bool = False,
        limit: int = 20,
        offset: int = 0,
        assigned_admin_id: uuid.UUID | None = None,
        include_all_assignments: bool = False,
    ) -> tuple[list[ProcurementRow], int]:
        from app.modules.admin.models import ProcurementCase
        from app.modules.auth.models import User
        from app.modules.auth.profile_models import FarmerProfile
        from app.modules.organic.repositories import OrganicRepository, organic_certification_display
        from app.modules.produce.models import ProduceOffer

        base = (
            select(ProduceOffer)
            .join(User, User.id == ProduceOffer.user_id)
            .outerjoin(ProcurementCase, ProcurementCase.offer_id == ProduceOffer.id)
            .where(ProduceOffer.is_deleted.is_(False))
        )
        if not include_all_assignments:
            base = base.where(
                or_(
                    ProcurementCase.id.is_(None),
                    ProcurementCase.assigned_admin_id.is_(None),
                    ProcurementCase.assigned_admin_id == assigned_admin_id,
                )
            )
        if crop:
            base = base.where(ProduceOffer.crop_name == crop)
        if category:
            base = base.where(ProduceOffer.product_category == category)
        if availability_type:
            base = base.where(ProduceOffer.availability_type == availability_type)
        if village:
            base = base.where(ProduceOffer.village == village)
        if district:
            base = base.where(ProduceOffer.district == district)
        if search:
            like = f"%{search.lower()}%"
            base = base.where(
                or_(
                    func.lower(ProduceOffer.listing_ref).like(like),
                    func.lower(User.farmer_ref).like(like),
                    func.lower(ProduceOffer.crop_name).like(like),
                )
            )
        if organic_only:
            from datetime import date as _date

            from app.modules.organic.models import OrganicFarmProfile

            base = base.where(
                ProduceOffer.farm_id.in_(
                    select(OrganicFarmProfile.farm_id).where(
                        OrganicFarmProfile.certification_status == "verified",
                        OrganicFarmProfile.certificate_expires_on.is_not(None),
                        OrganicFarmProfile.certificate_expires_on >= _date.today(),
                    )
                )
            )

        total = int(
            (
                await self.session.execute(select(func.count()).select_from(base.subquery()))
            ).scalar_one()
        )
        offers = (
            (
                await self.session.execute(
                    base.order_by(ProduceOffer.expected_harvest_date.asc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )

        organic_profiles = await OrganicRepository(self.session).profiles_for_farms(
            list({o.farm_id for o in offers})
        )

        user_ids = [o.user_id for o in offers]
        profiles: dict[uuid.UUID, object] = {}
        users: dict[uuid.UUID, object] = {}
        if user_ids:
            prows = (
                (
                    await self.session.execute(
                        select(FarmerProfile).where(FarmerProfile.user_id.in_(user_ids))
                    )
                )
                .scalars()
                .all()
            )
            profiles = {p.user_id: p for p in prows}
            urows = (
                (await self.session.execute(select(User).where(User.id.in_(user_ids))))
                .scalars()
                .all()
            )
            users = {u.id: u for u in urows}

        rows = [
            ProcurementRow(
                offer_id=o.id,
                listing_ref=o.listing_ref,
                farmer_ref=getattr(users.get(o.user_id), "farmer_ref", "—"),
                user_id=o.user_id,
                crop=o.crop_name,
                product_category=o.product_category,
                availability_type=o.availability_type,
                variety=o.variety,
                quantity=o.quantity,
                unit=o.unit,
                expected_grade=o.expected_grade,
                harvest_date=_as_dt(o.expected_harvest_date),
                village=o.village,
                district=o.district,
                farmer_name=getattr(profiles.get(o.user_id), "full_name", None),
                farmer_phone=None,
                offer_status=o.status,
                cultivated_area_hectares=o.cultivated_area_hectares,
                expected_total_quantity=o.expected_total_quantity,
                available_quantity=o.available_quantity,
                quantity_provenance=o.quantity_provenance,
                quality_notes=o.quality_notes,
                packaging=o.packaging,
                asking_price=o.asking_price,
                price_unit=o.price_unit,
                negotiable=o.negotiable,
                pickup_available=o.pickup_available,
                pickup_location=o.pickup_location,
                organic_certification_status=organic_certification_display(
                    organic_profiles.get(o.farm_id)
                )[0],
                organic_certification_verified=organic_certification_display(
                    organic_profiles.get(o.farm_id)
                )[1],
            )
            for o in offers
        ]
        return rows, total

    async def procurement_offer(self, offer_id: uuid.UUID) -> ProcurementRow | None:
        """Load the updated target directly; avoids scanning a paginated queue."""
        from app.modules.auth.models import User
        from app.modules.auth.profile_models import FarmerProfile
        from app.modules.organic.repositories import OrganicRepository, organic_certification_display
        from app.modules.produce.models import ProduceOffer

        offer = await self.session.get(ProduceOffer, offer_id)
        if offer is None or offer.is_deleted:
            return None
        profile = (
            await self.session.execute(
                select(FarmerProfile).where(FarmerProfile.user_id == offer.user_id)
            )
        ).scalar_one_or_none()
        user = await self.session.get(User, offer.user_id)
        organic_profile = (
            await OrganicRepository(self.session).profiles_for_farms([offer.farm_id])
        ).get(offer.farm_id)
        organic_status, organic_verified = organic_certification_display(organic_profile)
        return ProcurementRow(
            offer_id=offer.id,
            listing_ref=offer.listing_ref,
            farmer_ref=getattr(user, "farmer_ref", "—"),
            user_id=offer.user_id,
            crop=offer.crop_name,
            product_category=offer.product_category,
            availability_type=offer.availability_type,
            variety=offer.variety,
            quantity=offer.quantity,
            unit=offer.unit,
            expected_grade=offer.expected_grade,
            harvest_date=_as_dt(offer.expected_harvest_date),
            village=offer.village,
            district=offer.district,
            farmer_name=getattr(profile, "full_name", None),
            farmer_phone=None,
            offer_status=offer.status,
            cultivated_area_hectares=offer.cultivated_area_hectares,
            expected_total_quantity=offer.expected_total_quantity,
            available_quantity=offer.available_quantity,
            quantity_provenance=offer.quantity_provenance,
            quality_notes=offer.quality_notes,
            packaging=offer.packaging,
            asking_price=offer.asking_price,
            price_unit=offer.price_unit,
            negotiable=offer.negotiable,
            pickup_available=offer.pickup_available,
            pickup_location=offer.pickup_location,
            organic_certification_status=organic_status,
            organic_certification_verified=organic_verified,
        )

    async def procurement_facts(
        self, *, assigned_admin_id: uuid.UUID | None = None, include_all_assignments: bool = False
    ):  # noqa: ANN201
        """All offers as minimal analytics facts (village/crop/harvest/quantity)."""
        from app.modules.admin.engine import ProcurementFact
        from app.modules.admin.models import ProcurementCase
        from app.modules.produce.models import ProduceOffer

        stmt = (
            select(
                ProduceOffer.village,
                ProduceOffer.crop_name,
                ProduceOffer.expected_harvest_date,
                ProduceOffer.quantity,
                ProduceOffer.unit,
            )
            .outerjoin(ProcurementCase, ProcurementCase.offer_id == ProduceOffer.id)
            .where(ProduceOffer.is_deleted.is_(False))
        )
        if not include_all_assignments:
            stmt = stmt.where(
                or_(
                    ProcurementCase.id.is_(None),
                    ProcurementCase.assigned_admin_id.is_(None),
                    ProcurementCase.assigned_admin_id == assigned_admin_id,
                )
            )

        offers = (
            await self.session.execute(
                stmt
            )
        ).all()
        return [
            ProcurementFact(
                village=village, crop=crop, harvest_date=harvest, quantity=qty, unit=unit
            )
            for village, crop, harvest, qty, unit in offers
        ]

    async def offer_exists(self, offer_id: uuid.UUID) -> bool:
        from app.modules.produce.models import ProduceOffer

        res = await self.session.execute(
            select(ProduceOffer.id).where(
                ProduceOffer.id == offer_id, ProduceOffer.is_deleted.is_(False)
            )
        )
        return res.scalar_one_or_none() is not None

    # ----------------------------------------------------------------- #
    # Broadcast targeting
    # ----------------------------------------------------------------- #
    async def recipient_ids(self, target_type: str, target_value: str | None) -> list[uuid.UUID]:
        """Farmer user_ids matching a broadcast target (village/district/crop/language/all)."""
        from app.modules.auth.profile_models import FarmerProfile

        base = select(FarmerProfile.user_id).where(FarmerProfile.is_deleted.is_(False))
        if target_type == "village" and target_value:
            base = base.where(FarmerProfile.village == target_value)
        elif target_type == "district" and target_value:
            base = base.where(FarmerProfile.district == target_value)
        elif target_type == "crop" and target_value:
            base = base.where(FarmerProfile.primary_crop == target_value)
        elif target_type == "language" and target_value:
            base = base.where(FarmerProfile.language == target_value)
        rows = (await self.session.execute(base)).scalars().all()
        return list(rows)


def _as_dt(value) -> datetime | None:  # noqa: ANN001
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime(value.year, value.month, value.day)
