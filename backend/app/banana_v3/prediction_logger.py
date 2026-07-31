"""Privacy-minimized append-only prediction audit log."""
from __future__ import annotations

import json
import threading
from pathlib import Path


class JsonlLogger:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()

    def append(self, record: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        safe = {key: value for key, value in record.items() if value is not None}
        with self._lock, self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(safe, separators=(",", ":"), default=str) + "\n")
