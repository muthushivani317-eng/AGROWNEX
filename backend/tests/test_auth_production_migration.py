"""Production auth-deployment regression tests."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from app.modules.auth import service as service_module
from app.modules.auth.service import AuthService


def test_production_container_applies_migrations_before_uvicorn() -> None:
    dockerfile = (Path(__file__).parents[1] / "Dockerfile.production").read_text(
        encoding="utf-8"
    )
    command = next(line for line in dockerfile.splitlines() if line.startswith("CMD "))
    assert "alembic upgrade head && exec uvicorn" in command
    assert command.index("alembic upgrade head") < command.index("exec uvicorn")


async def test_auth_diagnostics_do_not_log_identity_or_token(
    db_session, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    sensitive_token = "token-value-that-must-never-be-logged"
    sensitive_uid = "firebase-uid-that-must-never-be-logged"
    sensitive_phone = "+91" + ("9" * 10)
    monkeypatch.setattr(
        service_module,
        "verify_id_token",
        lambda _token: {
            "uid": sensitive_uid,
            "phone_number": sensitive_phone,
            "email": None,
            "email_verified": False,
        },
    )

    with caplog.at_level(logging.INFO):
        result = await AuthService(db_session).verify_otp(
            sensitive_token, device_name="test", device_type="android"
        )

    assert result.user.firebase_uid == sensitive_uid
    rendered = caplog.text
    assert sensitive_token not in rendered
    assert sensitive_uid not in rendered
    assert sensitive_phone not in rendered


async def test_session_failure_reports_only_safe_stage(
    db_session, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    sensitive_token = "failed-token-that-must-never-be-logged"
    sensitive_phone = "+91" + ("8" * 10)
    monkeypatch.setattr(
        service_module,
        "verify_id_token",
        lambda _token: {
            "uid": "safe-test-uid",
            "phone_number": sensitive_phone,
            "email": None,
            "email_verified": False,
        },
    )

    async def fail_session(_entity):
        raise RuntimeError("sanitized test database failure")

    service = AuthService(db_session)
    monkeypatch.setattr(service.sessions, "add", fail_session)
    with caplog.at_level(logging.ERROR), pytest.raises(RuntimeError):
        await service.verify_otp(
            sensitive_token, device_name="test", device_type="android"
        )

    assert "stage=session_creation" in caplog.text
    assert "exception=RuntimeError" in caplog.text
    assert sensitive_token not in caplog.text
    assert sensitive_phone not in caplog.text
