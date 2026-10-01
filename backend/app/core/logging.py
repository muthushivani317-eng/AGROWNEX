"""Structured logging + optional Sentry (docs/CODING_STANDARDS.md → Logging).

Human-readable in dev, JSON in production (``LOG_JSON`` overrides). A scrubbing
filter redacts obvious secrets (tokens, OTPs, phone numbers, Authorization
headers) so they never reach logs — never log tokens, OTP values, full phone
numbers, or image bytes.
"""
from __future__ import annotations

import json
import logging
import re
import sys

from app.core.config import settings

_CONFIGURED = False

# Patterns redacted from every log record's message (defense in depth).
_SCRUB_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(otp[\"'=:\s]+)(\d{4,8})", re.IGNORECASE), r"\1***"),
    # Redact the actual credential after "authorization", keeping a "Bearer" label.
    (
        re.compile(r"(authorization[\"'=:\s]+)(bearer\s+)?(\S+)", re.IGNORECASE),
        r"\1\2***",
    ),
    (re.compile(r"(\+?\d{2})(\d{5,})(\d{2})"), r"\1***\3"),  # phone middle digits
)


def _scrub(message: str) -> str:
    for pattern, repl in _SCRUB_PATTERNS:
        message = pattern.sub(repl, message)
    return message


class ScrubFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.msg = _scrub(record.getMessage())
            record.args = ()
        except Exception:  # noqa: BLE001 - logging must never raise
            pass
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    level = logging.DEBUG if settings.debug else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(ScrubFilter())
    if settings.use_json_logs:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    _CONFIGURED = True


def _drop_expected_client_errors(event: dict, hint: dict) -> dict | None:
    """Keep Sentry for real faults: expected 4xx outcomes (wrong OTP, expired
    login, validation) are normal traffic, not incidents."""
    exc_info = hint.get("exc_info")
    if exc_info:
        from app.core.exceptions import AppError

        exc = exc_info[1]
        if isinstance(exc, AppError) and getattr(exc, "status_code", 500) < 500:
            return None
    return event


def init_sentry() -> bool:
    """Initialise Sentry when SENTRY_DSN is set; no-op (and safe) otherwise.

    Returns True if Sentry was initialised. Never a hard dependency: if the SDK
    isn't installed we log and continue rather than crash the app.
    """
    if not settings.sentry_dsn:
        return False
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            traces_sample_rate=0.0,
            send_default_pii=False,  # never ship farmer PII to Sentry
            # Stack-frame locals and request bodies can hold phone numbers,
            # OTP/ID tokens and farm GPS; keep them out of error reports.
            include_local_variables=False,
            max_request_body_size="never",
            before_send=_drop_expected_client_errors,
        )
        get_logger("observability").info("Sentry initialised")
        return True
    except ImportError:
        get_logger("observability").warning(
            "SENTRY_DSN set but sentry-sdk not installed; skipping"
        )
        return False


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
