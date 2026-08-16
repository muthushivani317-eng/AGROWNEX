import base64
import binascii
import hashlib
import io
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError

MAX_EVIDENCE_BYTES = 10 * 1024 * 1024
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}


class EvidenceValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ValidatedEvidence:
    data: bytes
    sha256: str
    width: int
    height: int


def validate_evidence(image_base64: str, mime_type: str, *, consent: bool) -> ValidatedEvidence:
    if not consent:
        raise EvidenceValidationError("EVIDENCE_RETENTION_CONSENT_REQUIRED")
    if mime_type not in ALLOWED_MIME:
        raise EvidenceValidationError("UNSUPPORTED_EVIDENCE_MIME")
    try:
        data = base64.b64decode(image_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise EvidenceValidationError("CORRUPT_EVIDENCE") from exc
    if not data or len(data) > MAX_EVIDENCE_BYTES:
        raise EvidenceValidationError("EVIDENCE_SIZE_INVALID")
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            width, height = image.size
    except (UnidentifiedImageError, OSError) as exc:
        raise EvidenceValidationError("CORRUPT_EVIDENCE") from exc
    if min(width, height) < 96:
        raise EvidenceValidationError("EVIDENCE_TOO_SMALL")
    return ValidatedEvidence(data, hashlib.sha256(data).hexdigest(), width, height)
