"""Short-lived, fail-closed confirmation receipts for controlled beta testing.

The store is intentionally process-local: a restart or another worker loses the
receipt and therefore blocks inference. A shared durable store is a pilot-release
blocker; this implementation never fails open.
"""

from __future__ import annotations

import hashlib
import secrets
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from .schemas import SupportedCropId

RECEIPT_TTL = timedelta(minutes=15)


@dataclass
class PendingIdentification:
    request_id: str
    actor_id: str
    image_sha256: str
    identified_crop: SupportedCropId | None
    created_at: datetime
    expires_at: datetime
    suggestion_token: str
    confirmation_token: str | None = None
    confirmed_crop: SupportedCropId | None = None
    consumed_at: datetime | None = None


class ConfirmationError(ValueError):
    pass


class ConfirmationStore:
    def __init__(self) -> None:
        self._records: dict[str, PendingIdentification] = {}
        self._lock = threading.RLock()

    def create(
        self, *, actor_id: str, image: bytes, identified_crop: SupportedCropId | None
    ) -> PendingIdentification:
        now = datetime.now(UTC)
        record = PendingIdentification(
            request_id=secrets.token_hex(16),
            actor_id=actor_id,
            image_sha256=hashlib.sha256(image).hexdigest(),
            identified_crop=identified_crop,
            created_at=now,
            expires_at=now + RECEIPT_TTL,
            suggestion_token=secrets.token_urlsafe(32),
        )
        with self._lock:
            self._records[record.request_id] = record
        return record

    def confirm(
        self,
        *,
        actor_id: str,
        request_id: str,
        confirmed_crop: SupportedCropId,
        correction: bool,
        suggestion_token: str | None = None,
    ) -> PendingIdentification:
        with self._lock:
            record = self._records.get(request_id)
            if record is None:
                raise ConfirmationError("CROP_ID_REQUEST_NOT_FOUND")
            if datetime.now(UTC) >= record.expires_at:
                self._records.pop(request_id, None)
                raise ConfirmationError("CROP_CONFIRMATION_EXPIRED")
            if not secrets.compare_digest(record.actor_id, actor_id):
                raise ConfirmationError("CROP_ID_REQUEST_OWNERSHIP_MISMATCH")
            if record.confirmation_token is not None:
                raise ConfirmationError("CROP_CONFIRMATION_ALREADY_USED")
            if suggestion_token is not None and not secrets.compare_digest(
                record.suggestion_token, suggestion_token
            ):
                raise ConfirmationError("CROP_CONFIRMATION_TOKEN_MISMATCH")
            if not correction and record.identified_crop != confirmed_crop:
                raise ConfirmationError("CROP_SELECTION_MISMATCH")
            record.confirmed_crop = confirmed_crop
            record.confirmation_token = secrets.token_urlsafe(32)
            return record

    def validate(
        self, *, actor_id: str, token: str, crop: str, image: bytes
    ) -> PendingIdentification:
        image_hash = hashlib.sha256(image).hexdigest()
        with self._lock:
            record = next(
                (item for item in self._records.values() if item.confirmation_token == token),
                None,
            )
            if record is None:
                raise ConfirmationError("CROP_CONFIRMATION_REQUIRED")
            if datetime.now(UTC) >= record.expires_at:
                raise ConfirmationError("CROP_CONFIRMATION_EXPIRED")
            if not secrets.compare_digest(record.actor_id, actor_id):
                raise ConfirmationError("CROP_ID_REQUEST_OWNERSHIP_MISMATCH")
            if record.confirmed_crop != crop:
                raise ConfirmationError("CROP_SELECTION_MISMATCH")
            if not secrets.compare_digest(record.image_sha256, image_hash):
                raise ConfirmationError("CROP_IMAGE_MISMATCH")
            if record.consumed_at is not None:
                raise ConfirmationError("CROP_CONFIRMATION_REPLAYED")
            record.consumed_at = datetime.now(UTC)
            return record


confirmation_store = ConfirmationStore()
