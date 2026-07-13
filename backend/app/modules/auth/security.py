"""Token & OTP hashing helpers (docs/SECURITY.md).

Refresh tokens are stored only as HMAC-SHA256 hashes (peppered with the server
secret), never in plaintext. Comparisons are constant-time.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets

from app.core.config import settings


def generate_refresh_token() -> tuple[str, str]:
    """Return a `(plaintext, hash)` pair. Only the hash is persisted."""
    plaintext = secrets.token_urlsafe(48)
    return plaintext, hash_token(plaintext)


def hash_token(plaintext: str) -> str:
    """Peppered HMAC-SHA256 of a token/fingerprint."""
    return hmac.new(
        settings.session_secret.encode("utf-8"),
        plaintext.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_token(plaintext: str, token_hash: str) -> bool:
    """Constant-time comparison of a token against its stored hash."""
    return hmac.compare_digest(hash_token(plaintext), token_hash)
