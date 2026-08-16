"""Map private model failures to stable, non-sensitive API categories."""
from __future__ import annotations


def classify_runtime_error(exc: BaseException) -> str:
    category = type(exc).__name__.upper()
    code = str(exc).upper()
    if code.startswith("ARTIFACT_MISSING:") or "FILE_MISSING" in code:
        return "MODEL_ARTIFACT_MISSING"
    if isinstance(exc, ImportError | OSError) or any(
        marker in code for marker in ("RUNTIME_PACKAGE_MISSING", "LOAD_FAILED")
    ):
        return "MODEL_RUNTIME_UNAVAILABLE"
    if any(marker in category for marker in ("INTEGRITY", "VERIFICATION")) or any(
        marker in code for marker in ("INTEGRITY", "HASH", "MANIFEST", "CHECKSUM")
    ):
        return "MODEL_INTEGRITY_FAILURE"
    return "MODEL_RUNTIME_UNAVAILABLE"
