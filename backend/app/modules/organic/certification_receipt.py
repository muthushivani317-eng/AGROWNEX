from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.disease.storage import ObjectStorage
from app.modules.organic.models import OrganicUploadAttestation

CERTIFICATION_DOCUMENT = "certification_document"
LOGBOOK_EVIDENCE = "logbook_evidence"


def expected_object_prefix(user_id: uuid.UUID, farm_id: uuid.UUID) -> str:
    return f"organic-certificates/{user_id}/{farm_id}/"


def _receipt(attestation: OrganicUploadAttestation) -> str:
    message = (
        f"v1:{attestation.purpose}:{attestation.id}:{attestation.user_id}:"
        f"{attestation.farm_id}:{attestation.object_version}:"
        f"{attestation.issued_at.isoformat()}:{attestation.expires_at.isoformat()}"
    ).encode()
    key = hmac.new(
        settings.session_secret.encode(), b"organic-upload-receipt:v1", hashlib.sha256
    ).digest()
    return hmac.new(key, message, hashlib.sha256).hexdigest()


async def store_and_attest_upload(
    session: AsyncSession,
    storage: ObjectStorage,
    *,
    user_id: uuid.UUID,
    farm_id: uuid.UUID,
    purpose: str,
    data: bytes,
    mime_type: str,
    file_suffix: str = "bin",
    now: datetime | None = None,
) -> tuple[OrganicUploadAttestation, str]:
    """Trusted upload seam: attest only bytes this process successfully writes."""
    if purpose not in {CERTIFICATION_DOCUMENT, LOGBOOK_EVIDENCE} or not data:
        raise ValueError("INVALID_UPLOAD_ATTESTATION")
    now = now or datetime.now(UTC)
    version = uuid.uuid4().hex
    prefix = "organic-certificates" if purpose == CERTIFICATION_DOCUMENT else "organic-evidence"
    key = f"{prefix}/{user_id}/{farm_id}/{version}.{file_suffix.lstrip('.')}"
    await storage.put(key=key, data=data, content_type=mime_type)
    row = OrganicUploadAttestation(
        user_id=user_id,
        farm_id=farm_id,
        purpose=purpose,
        object_key=key,
        object_version=version,
        sha256=hashlib.sha256(data).hexdigest(),
        file_size=len(data),
        mime_type=mime_type,
        issued_at=now,
        expires_at=now + timedelta(minutes=30),
    )
    session.add(row)
    await session.flush()
    return row, _receipt(row)


def upload_receipt_is_valid(
    *,
    attestation: OrganicUploadAttestation,
    user_id: uuid.UUID,
    farm_id: uuid.UUID,
    purpose: str,
    receipt: str,
    now: datetime | None = None,
) -> bool:
    now = now or datetime.now(UTC)
    prefix = (
        expected_object_prefix(user_id, farm_id)
        if purpose == CERTIFICATION_DOCUMENT
        else f"organic-evidence/{user_id}/{farm_id}/"
    )
    return bool(
        attestation.user_id == user_id
        and attestation.farm_id == farm_id
        and attestation.purpose == purpose
        and attestation.consumed_at is None
        and attestation.issued_at <= now <= attestation.expires_at
        and attestation.object_version
        and attestation.object_key.startswith(prefix)
        and hmac.compare_digest(_receipt(attestation), receipt)
    )
