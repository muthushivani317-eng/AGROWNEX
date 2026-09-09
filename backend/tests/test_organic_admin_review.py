from datetime import UTC, date, datetime, timedelta

import pytest
from app.modules.admin.constants import AdminRole
from app.modules.admin.exceptions import PermissionDeniedError
from app.modules.admin.models import AuditLog
from app.modules.admin.seed import ensure_admin
from app.modules.admin.service import AdminService
from app.modules.auth.models import User
from app.modules.disease.storage import MockStorage
from app.modules.farms.models import Farm
from app.modules.organic.admin_service import OrganicAdminService
from app.modules.organic.certification_receipt import (
    CERTIFICATION_DOCUMENT,
    store_and_attest_upload,
)
from app.modules.organic.ingestion import seed_public_source_pack
from app.modules.organic.models import OrganicCertificationDocument, OrganicFarmProfile
from sqlalchemy import select


async def _user(session, uid):
    user = User(firebase_uid=uid, status="active")
    session.add(user)
    await session.flush()
    return user


async def _context(session, role):
    user = await _user(session, f"admin-{role}")
    await ensure_admin(session, user.id, role=role, full_name="Reviewer")
    return await AdminService(session).resolve_admin(user, ip_address="127.0.0.1")


async def test_certification_review_requires_manage_content_and_audits(db_session):
    farmer = await _user(db_session, "cert-farmer")
    farm = Farm(user_id=farmer.id, name="Certified candidate")
    db_session.add(farm)
    await db_session.flush()
    profile = OrganicFarmProfile(
        farm_id=farm.id,
        mode="fully_organic",
        certification_status="document_submitted",
        certificate_expires_on=date.today() + timedelta(days=90),
    )
    db_session.add(profile)
    await db_session.flush()
    attestation, _ = await store_and_attest_upload(
        db_session,
        MockStorage(),
        user_id=farmer.id,
        farm_id=farm.id,
        purpose=CERTIFICATION_DOCUMENT,
        data=b"certificate",
        mime_type="application/pdf",
        file_suffix="pdf",
    )
    attestation.consumed_at = datetime.now(UTC)
    db_session.add(
        OrganicCertificationDocument(
            profile_id=profile.id,
            uploaded_by=farmer.id,
            upload_attestation_id=attestation.id,
            object_key=attestation.object_key,
            file_name="certificate.pdf",
            mime_type="application/pdf",
            file_size=attestation.file_size,
            sha256=attestation.sha256,
            idempotency_key="review-doc-1",
        )
    )
    await db_session.flush()

    denied = await _context(db_session, AdminRole.CUSTOMER_SUPPORT.value)
    with pytest.raises(PermissionDeniedError):
        await OrganicAdminService(db_session).review_certification(
            denied,
            profile.id,
            decision="verified",
            reason="reviewed document",
            expected_plan_version=profile.plan_version,
        )

    allowed = await _context(db_session, AdminRole.AGRICULTURE_OFFICER.value)
    reviewed = await OrganicAdminService(db_session, now=datetime.now(UTC)).review_certification(
        allowed,
        profile.id,
        decision="verified",
        reason="document confirmed",
        expected_plan_version=profile.plan_version,
    )
    assert reviewed.certification_status == "verified"
    audit = await db_session.scalar(
        select(AuditLog).where(AuditLog.action == "organic_certification_reviewed")
    )
    assert audit is not None
    assert audit.meta["decision"] == "verified"


async def test_input_promotion_requires_manage_content_and_audits_reviewer(db_session):
    item = (await seed_public_source_pack(db_session))[0]
    denied = await _context(db_session, AdminRole.CUSTOMER_SUPPORT.value)
    with pytest.raises(PermissionDeniedError):
        await OrganicAdminService(db_session).promote_input(
            denied, item.id, reason="source checked"
        )

    allowed = await _context(db_session, AdminRole.AGRICULTURE_OFFICER.value)
    promoted = await OrganicAdminService(db_session).promote_input(
        allowed, item.id, reason="official source and translation checked"
    )
    assert promoted.review_status == "approved"
    assert promoted.reviewed_by == allowed.admin.user_id
    audit = await db_session.scalar(
        select(AuditLog).where(AuditLog.action == "organic_input_promoted")
    )
    assert audit is not None
    assert audit.meta["content_hash"] == item.content_hash
