"""Unit tests for auth token/OTP hashing (docs/SECURITY.md)."""
from __future__ import annotations

from app.modules.auth.security import (
    generate_refresh_token,
    hash_token,
    verify_token,
)


def test_generate_refresh_token_returns_plain_and_hash() -> None:
    plain, token_hash = generate_refresh_token()
    assert plain and token_hash
    assert plain != token_hash  # the plaintext is never the stored value
    assert len(token_hash) == 64  # sha256 hex digest


def test_hash_is_deterministic_and_verifiable() -> None:
    plain, token_hash = generate_refresh_token()
    assert hash_token(plain) == token_hash
    assert verify_token(plain, token_hash) is True


def test_verify_rejects_wrong_token() -> None:
    _, token_hash = generate_refresh_token()
    assert verify_token("not-the-token", token_hash) is False


def test_tokens_are_unique() -> None:
    a, _ = generate_refresh_token()
    b, _ = generate_refresh_token()
    assert a != b
