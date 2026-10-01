from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.admin.constants import AdminPermission
from app.modules.admin.exceptions import PermissionDeniedError
from app.modules.admin.models import AuditLog
from app.modules.admin.service import AdminContext
from app.modules.disease.storage import ObjectStorage
from app.modules.organic.exceptions import (
    OrganicProfileNotFoundError,
    VerifiedCertificationLockedError,
)
from app.modules.organic.governance import input_hash_is_valid
from app.modules.organic.models import (
    OrganicCertificationDocument,
    OrganicFarmProfile,
    OrganicInput,
)


class OrganicAdminService:
    def __init__(self, session: AsyncSession, *, now: datetime | None = None) -> None:
        self.session = session
        self.now = now or datetime.now(UTC)

    async def certification_document_bytes(
        self, ctx: AdminContext, document_id: uuid.UUID, storage: ObjectStorage
    ) -> tuple[bytes, str, str]:
        if AdminPermission.MANAGE_CONTENT.value not in ctx.permissions:
            raise PermissionDeniedError()
        document = await self.session.get(OrganicCertificationDocument, document_id)
        if document is None or document.review_status == "rejected":
            raise ValueError("CERTIFICATION_DOCUMENT_NOT_AVAILABLE")
        data = await storage.get(key=document.object_key)
        if hashlib.sha256(data).hexdigest() != document.sha256 or len(data) != document.file_size:
            raise ValueError("CERTIFICATION_DOCUMENT_INTEGRITY_FAILED")
        # Every staff view of a farmer's certificate is recorded.
        self.session.add(
            AuditLog(
                admin_id=ctx.admin.id,
                role=ctx.admin.role,
                action="organic_certificate_viewed",
                target="organic_certification_document",
                target_id=str(document.id),
                ip_address=ctx.ip_address,
                meta={},
            )
        )
        await self.session.commit()
        return data, document.mime_type, document.file_name

    async def review_certification(
        self,
        ctx: AdminContext,
        profile_id: uuid.UUID,
        *,
        decision: str,
        reason: str,
        expected_plan_version: int,
    ) -> OrganicFarmProfile:
        if AdminPermission.MANAGE_CONTENT.value not in ctx.permissions:
            raise PermissionDeniedError()
        profile = await self.session.scalar(
            select(OrganicFarmProfile).where(OrganicFarmProfile.id == profile_id).with_for_update()
        )
        if profile is None:
            raise OrganicProfileNotFoundError()
        if profile.plan_version != expected_plan_version:
            raise VerifiedCertificationLockedError()
        if decision not in {"verified", "rejected"}:
            raise ValueError("INVALID_CERTIFICATION_DECISION")
        if decision == "verified":
            if not any(
                document.upload_attestation_id is not None and document.review_status != "rejected"
                for document in profile.documents
            ):
                raise ValueError("CERTIFICATION_DOCUMENT_REQUIRED")
            if (
                not profile.certificate_expires_on
                or profile.certificate_expires_on < self.now.date()
            ):
                raise ValueError("VALID_CERTIFICATE_EXPIRY_REQUIRED")
            profile.certification_verified_at = self.now
            profile.certification_verified_by = ctx.admin.user_id
        else:
            profile.certification_verified_at = None
            profile.certification_verified_by = None
        prior = profile.certification_status
        profile.certification_status = decision
        profile.plan_version += 1
        self.session.add(
            AuditLog(
                admin_id=ctx.admin.id,
                role=ctx.admin.role,
                action="organic_certification_reviewed",
                target="organic_farm_profile",
                target_id=str(profile.id),
                ip_address=ctx.ip_address,
                meta={
                    "prior_status": prior,
                    "decision": decision,
                    "reason": reason,
                    "expected_plan_version": expected_plan_version,
                    "result_plan_version": profile.plan_version,
                },
            )
        )
        await self.session.flush()
        return profile

    async def inputs_awaiting_review(self, ctx: AdminContext) -> list[OrganicInput]:
        if AdminPermission.MANAGE_CONTENT.value not in ctx.permissions:
            raise PermissionDeniedError()
        rows = await self.session.scalars(
            select(OrganicInput)
            .where(OrganicInput.review_status == "sourced_public_reference")
            .order_by(OrganicInput.category, OrganicInput.name_en)
        )
        return list(rows)

    async def promote_input(
        self, ctx: AdminContext, input_id: uuid.UUID, *, reason: str
    ) -> OrganicInput:
        if AdminPermission.MANAGE_CONTENT.value not in ctx.permissions:
            raise PermissionDeniedError()
        item = await self.session.scalar(
            select(OrganicInput).where(OrganicInput.id == input_id).with_for_update()
        )
        if item is None or item.review_status != "sourced_public_reference":
            raise ValueError("ORGANIC_INPUT_NOT_AWAITING_REVIEW")
        if not input_hash_is_valid(item):
            raise ValueError("ORGANIC_INPUT_SOURCE_HASH_INVALID")
        item.review_status = "approved"
        item.reviewed_by = ctx.admin.user_id
        item.reviewed_at = self.now
        self.session.add(
            AuditLog(
                admin_id=ctx.admin.id,
                role=ctx.admin.role,
                action="organic_input_promoted",
                target="organic_input",
                target_id=str(item.id),
                ip_address=ctx.ip_address,
                meta={
                    "reason": reason,
                    "source_version": item.source_version,
                    "content_hash": item.content_hash,
                },
            )
        )
        await self.session.flush()
        return item
