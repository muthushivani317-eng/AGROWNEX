from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from app.modules.auth.models import User
from app.modules.disease.storage import MockStorage
from app.modules.farms.models import Farm
from app.modules.organic.certification_receipt import (
    CERTIFICATION_DOCUMENT,
    store_and_attest_upload,
)
from app.modules.organic.exceptions import (
    InvalidCertificationUploadError,
    OrganicInputNotFoundError,
    VerifiedCertificationLockedError,
)
from app.modules.organic.governance import canonical_input_hash
from app.modules.organic.models import OrganicInput
from app.modules.organic.schemas import CertificationDocumentCreate, OrganicProfileWrite
from app.modules.organic.service import OrganicService


async def _user(session, uid: str, phone: str) -> User:
    row = User(
        firebase_uid=uid,
        phone_number=phone,
        email=None,
        is_phone_verified=True,
        is_email_verified=False,
        status="active",
    )
    session.add(row)
    await session.flush()
    return row


async def _farm(session, user: User, name: str) -> Farm:
    row = Farm(user_id=user.id, name=name)
    session.add(row)
    await session.flush()
    return row


async def test_profile_is_farm_scoped_and_idempotent(db_session):
    owner = await _user(db_session, "organic-owner", "+919000000101")
    other = await _user(db_session, "organic-other", "+919000000102")
    farm = await _farm(db_session, owner, "Organic field")
    service = OrganicService(db_session)
    payload = OrganicProfileWrite(
        mode="transitioning",
        transition_start_date=date(2026, 9, 1),
        goals=["soil_health"],
        preferred_practices=["green_manure"],
    )

    first = await service.upsert_profile(owner, farm.id, payload, "profile-request-001")
    second = await service.upsert_profile(owner, farm.id, payload, "profile-request-001")

    assert first.id == second.id
    assert first.plan_version == 1
    assert second.mode == "transitioning"
    with pytest.raises(Exception) as exc:
        await service.get_profile(other, farm.id)
    assert getattr(exc.value, "error_code", None) == "farm_not_found"


async def test_farmer_cannot_self_verify_certification():
    with pytest.raises(ValueError):
        OrganicProfileWrite(mode="fully_organic", certification_status="verified")


async def test_farmer_cannot_mutate_verified_certificate_fields(db_session):
    owner = await _user(db_session, "locked-cert-owner", "+919000000109")
    farm = await _farm(db_session, owner, "Verified certificate field")
    service = OrganicService(db_session)
    profile = await service.upsert_profile(
        owner,
        farm.id,
        OrganicProfileWrite(
            mode="fully_organic",
            certification_scheme="NPOP",
            certification_identifier="CERT-1",
            certificate_issued_on=date(2026, 1, 1),
            certificate_expires_on=date(2027, 1, 1),
        ),
        "locked-cert-create",
    )
    profile.certification_status = "verified"
    profile.certification_verified_at = datetime.now(UTC)
    await db_session.flush()

    with pytest.raises(VerifiedCertificationLockedError):
        await service.upsert_profile(
            owner,
            farm.id,
            OrganicProfileWrite(
                mode="fully_organic",
                certification_scheme="NPOP",
                certification_identifier="CERT-1",
                certificate_issued_on=date(2026, 1, 1),
                certificate_expires_on=date(2099, 1, 1),
            ),
            "locked-cert-attack",
        )


async def test_profile_write_preserves_omitted_pending_certification_fields(db_session):
    owner = await _user(db_session, "pending-cert-owner", "+919000000199")
    farm = await _farm(db_session, owner, "Pending certificate field")
    service = OrganicService(db_session)
    await service.upsert_profile(
        owner,
        farm.id,
        OrganicProfileWrite(
            mode="transitioning",
            certification_status="document_submitted",
            certification_scheme="NPOP",
            certification_identifier="PENDING-1",
        ),
        "pending-cert-create",
    )
    updated = await service.upsert_profile(
        owner,
        farm.id,
        OrganicProfileWrite(mode="fully_organic"),
        "pending-cert-profile-edit",
    )
    assert updated.certification_status == "document_submitted"
    assert updated.certification_scheme == "NPOP"
    assert updated.certification_identifier == "PENDING-1"


async def test_certificate_metadata_is_idempotent_and_safe(db_session):
    owner = await _user(db_session, "cert-owner", "+919000000103")
    farm = await _farm(db_session, owner, "Certificate field")
    service = OrganicService(db_session)
    await service.upsert_profile(
        owner, farm.id, OrganicProfileWrite(mode="fully_organic"), "profile-cert-001"
    )
    attestation, receipt = await store_and_attest_upload(
        db_session,
        MockStorage(),
        user_id=owner.id,
        farm_id=farm.id,
        purpose=CERTIFICATION_DOCUMENT,
        data=b"a" * 512,
        mime_type="application/pdf",
        file_suffix="pdf",
    )
    payload = CertificationDocumentCreate(
        upload_attestation_id=attestation.id,
        file_name="certificate.pdf",
        upload_receipt=receipt,
    )
    first = await service.add_document(owner, farm.id, payload, "document-request-001")
    second = await service.add_document(owner, farm.id, payload, "document-request-001")
    assert first.id == second.id
    assert first.object_key.startswith("organic-certificates/")

    bad = payload.model_copy(
        update={
            "upload_receipt": "0" * 64,
        }
    )
    with pytest.raises(InvalidCertificationUploadError):
        await service.add_document(owner, farm.id, bad, "document-request-002")


async def test_input_library_fails_closed_on_provenance_and_expiry(db_session):
    service = OrganicService(db_session)
    approved = OrganicInput(
        slug="verified-compost",
        category="compost",
        name_en="Compost",
        name_ta="உரம்",
        purpose_en="Soil amendment",
        purpose_ta="மண் மேம்பாடு",
        guidance={},
        applicable_crops=["paddy"],
        applicable_stages=[],
        applicable_regions=["Tamil Nadu"],
        limitations={},
        source_organization="TNAU",
        document_reference="Guide 1",
        source_url="https://example.invalid/guide",
        source_version="2026",
        content_hash="pending",
        review_status="approved",
        reviewed_at=datetime.now(UTC),
        review_due_on=date.today() + timedelta(days=30),
    )
    approved.content_hash = canonical_input_hash(approved)
    draft = OrganicInput(
        slug="draft-input",
        category="compost",
        name_en="Draft",
        name_ta="வரைவு",
        purpose_en="Draft",
        purpose_ta="வரைவு",
        guidance={},
        applicable_crops=["paddy"],
        applicable_stages=[],
        applicable_regions=[],
        limitations={},
        source_organization="TNAU",
        document_reference="Draft",
        source_url="https://example.invalid/draft",
        source_version="1",
        content_hash="c" * 64,
        review_status="draft",
    )
    db_session.add_all([approved, draft])
    await db_session.flush()

    rows, total = await service.list_inputs(
        category=None, crop="paddy", search=None, page=1, page_size=20
    )
    assert total == 1 and rows[0].id == approved.id
    with pytest.raises(OrganicInputNotFoundError):
        await service.get_input(draft.id)

    approved.purpose_en = "tampered after approval"
    rows, total = await service.list_inputs(
        category=None, crop="paddy", search=None, page=1, page_size=20
    )
    assert rows == [] and total == 0
