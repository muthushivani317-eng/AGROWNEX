from __future__ import annotations

import hashlib
import hmac
import uuid

from app.core.config import settings


def expected_object_prefix(user_id: uuid.UUID, farm_id: uuid.UUID) -> str:
    return f"organic-certificates/{user_id}/{farm_id}/"


def issue_upload_receipt(
    *, user_id: uuid.UUID, farm_id: uuid.UUID, object_key: str, sha256: str, file_size: int
) -> str:
    """Called by the protected upload completion path, never exposed as a farmer route."""
    message = f"{user_id}:{farm_id}:{object_key}:{sha256.lower()}:{file_size}".encode()
    return hmac.new(settings.session_secret.encode(), message, hashlib.sha256).hexdigest()


def upload_receipt_is_valid(
    *,
    user_id: uuid.UUID,
    farm_id: uuid.UUID,
    object_key: str,
    sha256: str,
    file_size: int,
    receipt: str,
) -> bool:
    if not object_key.startswith(expected_object_prefix(user_id, farm_id)):
        return False
    expected = issue_upload_receipt(
        user_id=user_id,
        farm_id=farm_id,
        object_key=object_key,
        sha256=sha256,
        file_size=file_size,
    )
    return hmac.compare_digest(expected, receipt)
