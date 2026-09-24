from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organic.governance import input_hash_is_valid
from app.modules.organic.models import (
    OrganicCertificationDocument,
    OrganicFarmProfile,
    OrganicInput,
)


def organic_certification_display(
    profile: OrganicFarmProfile | None,
) -> tuple[str | None, bool]:
    """(display_status, verified) for a farm's real organic certification --
    the exact expiry-aware logic already used by
    organic/service.py::OrganicService.farm_summary, extracted here so other
    modules (produce marketplace tagging/filtering) can reuse it instead of
    re-deriving their own version of "is this actually still verified."
    A farmer can never make this return True by themselves -- certification_status
    only ever becomes "verified" via an admin decision (admin_service.py).
    """
    if profile is None:
        return None, False
    status = profile.certification_status
    verified = bool(
        status == "verified"
        and profile.certificate_expires_on is not None
        and profile.certificate_expires_on >= date.today()
    )
    if status == "verified" and not verified:
        status = "expired"
    return status, verified


class OrganicSummaryFacts:
    def __init__(self, **values):
        self.__dict__.update(values)


class OrganicRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def profile_for_farm(self, farm_id: uuid.UUID) -> OrganicFarmProfile | None:
        result = await self.session.execute(
            select(OrganicFarmProfile).where(OrganicFarmProfile.farm_id == farm_id)
        )
        return result.scalar_one_or_none()

    async def profiles_for_farms(
        self, farm_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, OrganicFarmProfile]:
        """Batch lookup for list views (produce marketplace organic tagging) --
        avoids one query per row. Empty input short-circuits without a query."""
        if not farm_ids:
            return {}
        result = await self.session.execute(
            select(OrganicFarmProfile).where(OrganicFarmProfile.farm_id.in_(farm_ids))
        )
        return {p.farm_id: p for p in result.scalars().all()}

    async def document_by_key(
        self, profile_id: uuid.UUID, idempotency_key: str
    ) -> OrganicCertificationDocument | None:
        result = await self.session.execute(
            select(OrganicCertificationDocument).where(
                OrganicCertificationDocument.profile_id == profile_id,
                OrganicCertificationDocument.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def documents(self, profile_id: uuid.UUID) -> list[OrganicCertificationDocument]:
        result = await self.session.execute(
            select(OrganicCertificationDocument)
            .where(OrganicCertificationDocument.profile_id == profile_id)
            .order_by(OrganicCertificationDocument.created_at.desc())
        )
        return list(result.scalars())

    @staticmethod
    def approved_predicate(today: date):
        return (
            OrganicInput.review_status == "approved",
            OrganicInput.reviewed_at.is_not(None),
            OrganicInput.source_organization != "",
            OrganicInput.document_reference != "",
            OrganicInput.source_url != "",
            OrganicInput.source_version != "",
            OrganicInput.content_hash != "",
            or_(OrganicInput.effective_from.is_(None), OrganicInput.effective_from <= today),
            or_(OrganicInput.review_due_on.is_(None), OrganicInput.review_due_on >= today),
        )

    async def list_approved_inputs(
        self,
        *,
        today: date,
        category: str | None,
        crop: str | None,
        search: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[OrganicInput], int]:
        filters = list(self.approved_predicate(today))
        if category:
            filters.append(OrganicInput.category == category)
        if crop:
            # JSON arrays are portable but exact containment differs by database;
            # filter candidates in the service for consistent SQLite/Postgres behavior.
            pass
        if search:
            term = f"%{search.strip().lower()}%"
            filters.append(
                or_(
                    func.lower(OrganicInput.name_en).like(term),
                    func.lower(OrganicInput.name_ta).like(term),
                )
            )
        result = await self.session.execute(
            select(OrganicInput).where(*filters).order_by(OrganicInput.name_en, OrganicInput.id)
        )
        rows = [
            row
            for row in result.scalars()
            if not crop or crop.lower() in {str(v).lower() for v in row.applicable_crops}
        ]
        rows = [row for row in rows if input_hash_is_valid(row)]
        return rows[offset : offset + limit], len(rows)

    async def approved_input(self, input_id: uuid.UUID, today: date) -> OrganicInput | None:
        result = await self.session.execute(
            select(OrganicInput).where(OrganicInput.id == input_id, *self.approved_predicate(today))
        )
        item = result.scalar_one_or_none()
        return item if item is not None and input_hash_is_valid(item) else None

    async def summary_facts(self, user_id: uuid.UUID, farm_id: uuid.UUID) -> OrganicSummaryFacts:
        from app.modules.action_verification.models import ActionWorkflow
        from app.modules.organic_logbook.models import OrganicPracticeLogEntry
        from app.modules.produce.models import ProduceOffer, ProduceTraceBatch
        from app.modules.satellite.models import SatelliteAlert
        from app.modules.soil.models import SoilIndicatorEvidence, SoilProfile

        async def count(model, *where) -> int:
            return int((await self.session.scalar(select(func.count(model.id)).where(*where))) or 0)

        pending_actions = await count(
            ActionWorkflow,
            ActionWorkflow.user_id == user_id,
            ActionWorkflow.farm_id == farm_id,
            ActionWorkflow.source_module.like("organic%"),
            ActionWorkflow.status.in_(("suggested", "viewed", "deferred")),
            ActionWorkflow.is_deleted.is_(False),
        )
        logbook_count = await count(
            OrganicPracticeLogEntry,
            OrganicPracticeLogEntry.user_id == user_id,
            OrganicPracticeLogEntry.farm_id == farm_id,
            OrganicPracticeLogEntry.is_deleted.is_(False),
        )
        weather_advisories = await count(
            ActionWorkflow,
            ActionWorkflow.user_id == user_id,
            ActionWorkflow.farm_id == farm_id,
            ActionWorkflow.source_module == "weather",
            ActionWorkflow.is_deleted.is_(False),
        )
        satellite_advisories = await count(
            SatelliteAlert,
            SatelliteAlert.user_id == user_id,
            SatelliteAlert.farm_id == farm_id,
        )
        soil_profiles = await count(
            SoilProfile,
            SoilProfile.user_id == user_id,
            SoilProfile.farm_id == farm_id,
            SoilProfile.is_deleted.is_(False),
        )
        soil_evidence = await count(
            SoilIndicatorEvidence,
            SoilIndicatorEvidence.user_id == user_id,
            SoilIndicatorEvidence.farm_id == farm_id,
        )
        trace_batches = int(
            (
                await self.session.scalar(
                    select(func.count(ProduceTraceBatch.id))
                    .join(ProduceOffer, ProduceOffer.id == ProduceTraceBatch.offer_id)
                    .where(
                        ProduceTraceBatch.owner_user_id == user_id,
                        ProduceOffer.farm_id == farm_id,
                        ProduceOffer.is_deleted.is_(False),
                    )
                )
            )
            or 0
        )
        return OrganicSummaryFacts(
            pending_actions=pending_actions,
            logbook_count=logbook_count,
            weather_advisory_count=weather_advisories,
            satellite_advisory_count=satellite_advisories,
            soil_data_available=bool(soil_profiles or soil_evidence),
            traceability_batch_count=trace_batches,
        )
