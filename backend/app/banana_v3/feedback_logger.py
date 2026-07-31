"""Validated append-only feedback records."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from .prediction_logger import JsonlLogger
from .schemas import FeedbackRequest


class FeedbackLogger:
    def __init__(self, path: Path):
        self.logger = JsonlLogger(path)

    def log(self, feedback: FeedbackRequest) -> None:
        record = feedback.model_dump(mode="json")
        if record.get("notes"):
            notes = record["notes"]
            notes = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[REDACTED_EMAIL]", notes)
            notes = re.sub(r"(?<!\d)(?:\+?\d[\d -]{7,}\d)(?!\d)", "[REDACTED_PHONE]", notes)
            record["notes"] = notes
        record["timestamp"] = datetime.now(timezone.utc).isoformat()
        self.logger.append(record)
