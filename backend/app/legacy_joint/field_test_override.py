"""Process-local, fail-off authorization and separate audit for legacy-joint KVK tests."""
from __future__ import annotations

import hashlib
import json
import re
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import settings

TEST_MODE_MARKER = (
    "TEST MODE \u2014 NOT AUTHORIZED FOR GENERAL RELEASE \u2014 RESULT NOT VALIDATED"
)
_SESSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class LegacyJointFieldTestGate:
    """Permission is configuration; activation is volatile and resets on restart."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._session_id: str | None = None

    def activate(self, session_id: str) -> None:
        if settings.legacy_joint_field_test_override_permitted is not True:
            raise RuntimeError("LEGACY_JOINT_FIELD_TEST_OVERRIDE_NOT_PERMITTED")
        if not _SESSION_PATTERN.fullmatch(session_id):
            raise ValueError("INVALID_FIELD_TEST_SESSION_ID")
        with self._lock:
            self._session_id = session_id

    def deactivate(self) -> str | None:
        with self._lock:
            previous = self._session_id
            self._session_id = None
            return previous

    def require_active(self) -> str:
        with self._lock:
            if (
                settings.legacy_joint_field_test_override_permitted is not True
                or self._session_id is None
            ):
                raise RuntimeError("LEGACY_JOINT_FIELD_TEST_OVERRIDE_OFF")
            return self._session_id

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "permitted": settings.legacy_joint_field_test_override_permitted is True,
                "active": self._session_id is not None,
                "session_id": self._session_id,
                "resets_on_restart": True,
            }


class LegacyJointOverrideAuditLogger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()

    def record(
        self,
        *,
        event: str,
        session_id: str,
        tester: Any,
        crop: str | None = None,
        predicted_class: str | None = None,
        confidence: float | None = None,
        outcome: str | None = None,
    ) -> None:
        record = {
            "record_type": "LEGACY_JOINT_CONTROLLED_FIELD_TEST_OVERRIDE_AUDIT",
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "event": event,
            "session_id": session_id,
            "tester_subject_hash": hashlib.sha256(
                str(tester.user.id).encode()
            ).hexdigest()[:16],
            "tester_role": str(tester.role),
            "crop": crop,
            "model_id": "legacy_joint_v1_crop_constrained",
            "predicted_class": predicted_class,
            "confidence": confidence,
            "outcome": outcome,
            "test_mode_marker": TEST_MODE_MARKER,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, separators=(",", ":")) + "\n")


legacy_joint_field_test_gate = LegacyJointFieldTestGate()
legacy_joint_override_audit_logger = LegacyJointOverrideAuditLogger(
    Path(settings.legacy_joint_field_test_audit_path).resolve()
)
