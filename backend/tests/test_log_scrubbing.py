"""Secrets never reach logs, including inside exception tracebacks."""
import logging

from app.core.logging import JsonFormatter, ScrubbingFormatter, _scrub


def test_credentials_are_redacted():
    out = _scrub(
        "connect postgresql://agrow:S3cretPass@db:5432/x failed; api_key=sk-live-123 "
        "Authorization: Bearer eyJhbGc.abc.def refresh_token=rt-999 otp=123456"
    )
    for leaked in ("S3cretPass", "sk-live-123", "eyJhbGc", "rt-999", "123456"):
        assert leaked not in out
    assert "postgresql://***@db" in out


def test_exception_text_is_scrubbed_by_both_formatters():
    try:
        raise RuntimeError("redis://default:hunter2@cache:6379 unreachable")
    except RuntimeError:
        import sys

        record = logging.LogRecord("t", logging.ERROR, __file__, 1, "boom", (), sys.exc_info())
    assert "hunter2" not in ScrubbingFormatter("%(message)s").format(record)
    assert "hunter2" not in JsonFormatter().format(record)
