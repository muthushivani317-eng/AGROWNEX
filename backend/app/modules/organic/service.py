from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.action_verification.models import ActionWorkflow
from app.modules.action_verification.service import ActionVerificationService
from app.modules.auth.models import User
from app.modules.disease.exceptions import DiseaseReportNotFoundError
from app.modules.disease.repositories import DiseaseReportRepository
from app.modules.disease.storage import ObjectStorage
from app.modules.farms.service import FarmService
from app.modules.organic.certification_receipt import (
    CERTIFICATION_DOCUMENT,
    LOGBOOK_EVIDENCE,
    store_and_attest_upload,
    upload_receipt_is_valid,
)
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
    OrganicUploadAttestation,
)
from app.modules.organic.plan_engine import build_disease_plan, build_soil_plan
from app.modules.organic.repositories import OrganicRepository, organic_certification_display
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

    async def upload_and_attest(
        self,
        user: User,
        farm_id: uuid.UUID,
        *,
        purpose: str,
        data: bytes,
        mime_type: str,
        file_suffix: str,
        storage: ObjectStorage,
    ):
        await self.farms.get_farm(user, farm_id)
        allowed = {
            CERTIFICATION_DOCUMENT: {"application/pdf", "image/jpeg", "image/png"},
            LOGBOOK_EVIDENCE: {
                "application/pdf",
                "image/jpeg",
                "image/png",
                "audio/mpeg",
                "audio/mp4",
            },
        }
        if purpose not in allowed or mime_type not in allowed[purpose] or not data:
            raise InvalidCertificationUploadError()
        if len(data) > 15_000_000:
            raise InvalidCertificationUploadError()
        return await store_and_attest_upload(
            self.session,
            storage,
            user_id=user.id,
            farm_id=farm_id,
            purpose=purpose,
            data=data,
            mime_type=mime_type,
            file_suffix=file_suffix,
        )

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
                field in data.model_fields_set and getattr(data, field) != getattr(profile, field)
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
                if field in data.model_fields_set:
                    setattr(profile, field, getattr(data, field))
        # A farmer update cannot create or overwrite verified state.
        if not current_verified and "certification_status" in data.model_fields_set:
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
        existing = await self.repo.document_by_key(profile.id, idempotency_key)
        if existing:
            if (
                existing.upload_attestation_id != data.upload_attestation_id
                or existing.file_name != data.file_name
            ):
                raise InvalidCertificationUploadError()
            return existing
        attestation = await self.session.get(OrganicUploadAttestation, data.upload_attestation_id)
        if attestation is None or not upload_receipt_is_valid(
            attestation=attestation,
            user_id=user.id,
            farm_id=farm_id,
            purpose=CERTIFICATION_DOCUMENT,
            receipt=data.upload_receipt,
        ):
            logger.warning(
                "Rejected unverified organic certificate upload user=%s farm=%s", user.id, farm_id
            )
            raise InvalidCertificationUploadError()
        document = OrganicCertificationDocument(
            profile_id=profile.id,
            uploaded_by=user.id,
            idempotency_key=idempotency_key,
            upload_attestation_id=attestation.id,
            object_key=attestation.object_key,
            file_name=data.file_name,
            mime_type=attestation.mime_type,
            file_size=attestation.file_size,
            sha256=attestation.sha256,
        )
        attestation.consumed_at = datetime.now(UTC)
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

    async def catalogue_coverage(self) -> dict:
        rows = list((await self.session.scalars(select(OrganicInput))).all())
        categories: dict[str, int] = {}
        crops: dict[str, int] = {}
        for row in rows:
            categories[row.category] = categories.get(row.category, 0) + 1
            for crop in row.applicable_crops:
                crops[str(crop)] = crops.get(str(crop), 0) + 1
        return {
            "total": len(rows),
            "approved": sum(row.review_status == "approved" for row in rows),
            "awaiting_human_review": sum(
                row.review_status == "sourced_public_reference" for row in rows
            ),
            "draft": sum(row.review_status == "draft" for row in rows),
            "categories": categories,
            "crops": crops,
        }

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

    async def register_disease_action(
        self, user: User, report_id: uuid.UUID, action_code: str, source_record_id: str
    ):
        plan = await self.disease_plan(user, report_id)
        step = next(
            (
                item
                for item in plan.steps
                if item.source_action.action_code == action_code
                and item.source_action.source_record_id == source_record_id
            ),
            None,
        )
        report = await self.disease_reports.get_for_user(report_id, user.id)
        if step is None or report is None or report.farm_id is None:
            raise DiseaseReportNotFoundError()
        return await ActionVerificationService(self.session).register_source_action(
            user, report.farm_id, step.source_action
        )

    async def register_soil_action(
        self, user: User, farm_id: uuid.UUID, action_code: str, source_record_id: str
    ):
        plan = await self.soil_plan(user, farm_id)
        option = next(
            (
                item
                for item in plan.options
                if item.source_action.action_code == action_code
                and item.source_action.source_record_id == source_record_id
            ),
            None,
        )
        if option is None:
            raise OrganicInputNotFoundError()
        return await ActionVerificationService(self.session).register_source_action(
            user, farm_id, option.source_action
        )

    async def farm_plan(self, user: User, farm_id: uuid.UUID):
        await self.farms.get_farm(user, farm_id)
        rows = list(
            (
                await self.session.execute(
                    select(ActionWorkflow)
                    .where(
                        ActionWorkflow.user_id == user.id,
                        ActionWorkflow.farm_id == farm_id,
                        ActionWorkflow.is_deleted.is_(False),
                        ActionWorkflow.source_module.in_(
                            [
                                "organic_disease_plan",
                                "organic_soil_plan",
                                "organic_calendar",
                                "organic_weather_gate",
                                "satellite_field_scouting",
                                "satellite_scouting_followup",
                            ]
                        ),
                    )
                    .order_by(ActionWorkflow.created_at.desc())
                )
            ).scalars()
        )
        kinds = {
            "organic_disease_plan": "disease",
            "organic_soil_plan": "soil",
            "organic_calendar": "calendar",
            "organic_weather_gate": "weather",
            "satellite_field_scouting": "satellite",
            "satellite_scouting_followup": "satellite",
        }

        def state(row: ActionWorkflow) -> str:
            if row.status == "farmer_reported_done":
                return "completed"
            if row.source_module == "organic_weather_gate":
                return "waiting_for_weather"
            if "expert" in row.action_code or "review" in row.action_code:
                return "needs_confirmation"
            return "ready"

        return {
            "farm_id": farm_id,
            "generated_at": datetime.now(UTC),
            "actions": [
                {
                    "id": row.id,
                    "action_type": kinds[row.source_module],
                    "title": row.action_code,
                    "description": row.action_code,
                    "priority": 1,
                    "state": state(row),
                    "due_at": row.due_at,
                    "source_organization": row.source_module,
                    "source_reference": row.source_record_id,
                    "source_url": None,
                    "review_status": (
                        "verified"
                        if row.source_verified
                        else "farmer_reported"
                        if row.farmer_created
                        else "unverified"
                    ),
                    "source_action_id": row.source_record_id,
                    "scouting_only": row.source_module.startswith("satellite_"),
                }
                for row in rows
            ],
        }

    async def farm_summary(self, user: User, farm_id: uuid.UUID):
        await self.farms.get_farm(user, farm_id)
        profile = await self.repo.profile_for_farm(farm_id)
        facts = await self.repo.summary_facts(user.id, farm_id)
        certification_status, certification_verified = organic_certification_display(profile)
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
