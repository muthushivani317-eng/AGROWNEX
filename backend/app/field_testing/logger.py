"""Privacy-minimized append-only JSONL for supervised field-test predictions."""
from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_LOG_PATH = (
    Path(__file__).resolve().parents[2]
    / "logs"
    / "field_testing"
    / "controlled_predictions.jsonl"
)


class FieldTestLogger:
    """Write field-test-only records without images, tokens, phone numbers, or PII."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()

    def record(
        self,
        *,
        tester: Any,
        crop: str,
        model_id: str,
        predicted_class: str | None,
        confidence: float | None,
        outcome: str,
    ) -> None:
        user_id = str(tester.user.id)
        record = {
            "record_type": "KVK_CONTROLLED_FIELD_TEST_PREDICTION",
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "tester_subject_hash": hashlib.sha256(user_id.encode()).hexdigest()[:16],
            "tester_role": str(tester.role),
            "crop": crop,
            "model_id": model_id,
            "predicted_class": predicted_class,
            "confidence": confidence,
            "outcome": outcome,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, separators=(",", ":")) + "\n")


field_test_logger = FieldTestLogger(
    Path(os.getenv("AGROWAI_FIELD_TEST_LOG_PATH", str(DEFAULT_LOG_PATH))).resolve()
)
