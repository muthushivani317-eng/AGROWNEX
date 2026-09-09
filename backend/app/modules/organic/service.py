from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.auth.models import User
from app.modules.disease.exceptions import DiseaseReportNotFoundError
from app.modules.disease.repositories import DiseaseReportRepository
from app.modules.farms.service import FarmService
from app.modules.organic.certification_receipt import upload_receipt_is_valid
from app.modules.organic.exceptions import (
    InvalidCertificationUploadError,
    OrganicInputNotFoundError,
    OrganicProfileNotFoundError,
    VerifiedCertificationLockedError,
)
from app.modules.organic.models import (
    OrganicCertificationDocument,
    OrganicFarmProfile,
    OrganicInput,
)
from app.modules.organic.plan_engine import build_disease_plan, build_soil_plan
from app.modules.organic.repositories import OrganicRepository
from app.modules.organic.schemas import CertificationDocumentCreate, OrganicProfileWrite
from app.modules.soil.repository import SoilRepository

logger = get_logger("organic.service")


class OrganicService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = OrganicRepository(session)
        self.farms = FarmService(session)
        self.disease_reports = DiseaseReportRepository(session)
        self.soil = SoilRepository(session)

    async def get_profile(self, user: User, farm_id: uuid.UUID) -> OrganicFarmProfile:
        await self.farms.get_farm(user, farm_id)
        profile = await self.repo.profile_for_farm(farm_id)
        if profile is None:
            raise OrganicProfileNotFoundError()
        return profile

    async def upsert_profile(
        self, user: User, farm_id: uuid.UUID, data: OrganicProfileWrite, idempotency_key: str
    ) -> OrganicFarmProfile:
        await self.farms.get_farm(user, farm_id)
        profile = await self.repo.profile_for_farm(farm_id)
        is_new = profile is None
        if profile is not None and profile.last_idempotency_key == idempotency_key:
            return profile
        if profile is None:
            profile = OrganicFarmProfile(farm_id=farm_id)
            self.session.add(profile)
        current_verified = profile.certification_status == "verified"
        if current_verified:
            protected = (
                "certification_scheme",
                "certification_identifier",
                "certificate_issued_on",
                "certificate_expires_on",
            )
            if any(
                field in data.model_fields_set
                and getattr(data, field) != getattr(profile, field)
                for field in protected
            ):
                raise VerifiedCertificationLockedError()
        for field in (
            "mode",
            "transition_start_date",
            "goals",
            "preferred_practices",
            "avoided_input_categories",
        ):
            value = getattr(data, field)
            setattr(profile, field, value.value if hasattr(value, "value") else value)
        if not current_verified:
            for field in (
                "certification_scheme",
                "certification_identifier",
                "certificate_issued_on",
                "certificate_expires_on",
            ):
                setattr(profile, field, getattr(data, field))
        # A farmer update cannot create or overwrite verified state.
        if not current_verified:
            profile.certification_status = data.certification_status.value
        profile.last_idempotency_key = idempotency_key
        profile.plan_version = 1 if is_new else (profile.plan_version or 1) + 1
        await self.session.flush()
        await self.session.refresh(profile)
        return profile

    async def add_document(
        self,
        user: User,
        farm_id: uuid.UUID,
        data: CertificationDocumentCreate,
        idempotency_key: str,
    ) -> OrganicCertificationDocument:
        profile = await self.get_profile(user, farm_id)
        if not upload_receipt_is_valid(
            user_id=user.id,
            farm_id=farm_id,
            object_key=data.object_key,
            sha256=data.sha256,
            file_size=data.file_size,
            receipt=data.upload_receipt,
        ):
            logger.warning(
                "Rejected unverified organic certificate upload user=%s farm=%s", user.id, farm_id
            )
            raise InvalidCertificationUploadError()
        existing = await self.repo.document_by_key(profile.id, idempotency_key)
        if existing:
            return existing
        document = OrganicCertificationDocument(
            profile_id=profile.id,
            uploaded_by=user.id,
            idempotency_key=idempotency_key,
            **data.model_dump(exclude={"upload_receipt"}),
        )
        self.session.add(document)
        if profile.certification_status != "verified":
            profile.certification_status = "document_submitted"
        await self.session.flush()
        await self.session.refresh(document)
        return document

    async def list_documents(self, user: User, farm_id: uuid.UUID):
        profile = await self.get_profile(user, farm_id)
        return await self.repo.documents(profile.id)

    async def list_inputs(self, *, category, crop, search, page, page_size):
        return await self.repo.list_approved_inputs(
            today=date.today(),
            category=category,
            crop=crop,
            search=search,
            limit=page_size,
            offset=(page - 1) * page_size,
        )

    async def get_input(self, input_id: uuid.UUID) -> OrganicInput:
        item = await self.repo.approved_input(input_id, date.today())
        if item is None:
            raise OrganicInputNotFoundError()
        return item

    async def disease_plan(self, user: User, report_id: uuid.UUID):
        report = await self.disease_reports.get_for_user(report_id, user.id)
        if report is None:
            raise DiseaseReportNotFoundError()
        if report.farm_id is not None:
            await self.farms.get_farm(user, report.farm_id)
        inputs, _ = await self.repo.list_approved_inputs(
            today=date.today(),
            category=None,
            crop=report.crop,
            search=None,
            limit=10_000,
            offset=0,
        )
        return build_disease_plan(report, inputs)

    async def soil_plan(self, user: User, farm_id: uuid.UUID):
        farm = await self.farms.get_farm(user, farm_id)
        profile = await self.soil.get_profile(user.id, farm_id)
        evidence = await self.soil.list_evidence(user.id, farm_id)
        inputs, _ = await self.repo.list_approved_inputs(
            today=date.today(),
            category=None,
            crop=farm.crop,
            search=None,
            limit=10_000,
            offset=0,
        )
        return build_soil_plan(farm, profile, evidence, inputs)

    async def farm_summary(self, user: User, farm_id: uuid.UUID):
        await self.farms.get_farm(user, farm_id)
        profile = await self.repo.profile_for_farm(farm_id)
        facts = await self.repo.summary_facts(user.id, farm_id)
        certification_status = profile.certification_status if profile else None
        certification_verified = certification_status == "verified"
        traceability_ready = bool(profile is not None and facts.logbook_count > 0)
        logger.info(
            "Organic farm summary user=%s farm=%s profile=%s pending=%s logbook=%s",
            user.id,
            farm_id,
            profile is not None,
            facts.pending_actions,
            facts.logbook_count,
        )
        return {
            "farm_id": farm_id,
            "profile": profile,
            "certification_status": certification_status,
            "certification_verified": certification_verified,
            "soil_plan_available": facts.soil_data_available,
            "pending_organic_actions": facts.pending_actions,
            "logbook_entries": facts.logbook_count,
            "weather_advisory_available": facts.weather_advisory_count > 0,
            "satellite_advisory_available": facts.satellite_advisory_count > 0,
            "traceability_ready": traceability_ready,
            "traceability_batch_count": facts.traceability_batch_count,
        }
