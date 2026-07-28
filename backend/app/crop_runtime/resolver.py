from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path

from .registry import CropRegistry
from .schemas import ModelAvailabilityStatus, ModelUnavailableResponse

REQUIRED_RUNTIME_FILES = (
    "best.pt",
    "class_to_index.json",
    "index_to_class.json",
    "preprocessing.json",
    "temperature.json",
    "selected_thresholds.json",
    "abstention_policy.json",
    "runtime_config.json",
    "SHA256SUMS.txt",
    "FROZEN_DECISION_RECORD.md",
)
FORBIDDEN_RUNTIME_MARKERS = ("provisional_test", "sealed_test", "test_logits")
logger = logging.getLogger("crop_runtime")


class ModelNotAvailableError(RuntimeError):
    def __init__(self, response: ModelUnavailableResponse) -> None:
        super().__init__(response.status)
        self.response = response


class RuntimeIntegrityError(RuntimeError):
    pass


@dataclass(frozen=True)
class VerifiedRuntime:
    crop_id: str
    root: Path
    class_to_index: dict[str, int]
    preprocessing: dict
    temperature: dict
    thresholds: dict
    abstention_policy: dict


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class RuntimeResolver:
    def __init__(self, registry: CropRegistry, project_root: Path) -> None:
        self.registry = registry
        self.project_root = project_root.resolve()

    def unavailable(self, crop_id: str) -> ModelUnavailableResponse:
        entry = self.registry.get(crop_id)
        return ModelUnavailableResponse(
            crop_id=entry.crop_id,
            message_en=entry.limitation_message_en,
            message_ta=entry.limitation_message_ta,
            limitation=entry.model_status,
        )

    def guard(self, crop_id: str) -> None:
        entry = self.registry.get(crop_id)
        logger.info("crop_selected", extra={"crop_id": entry.crop_id})
        if (
            not entry.crop_enabled
            or not entry.disease_detection_enabled
            or entry.model_status != ModelAvailabilityStatus.FROZEN_RUNTIME_READY
        ):
            logger.info(
                "model_unavailable",
                extra={"crop_id": entry.crop_id, "model_status": entry.model_status.value},
            )
            raise ModelNotAvailableError(self.unavailable(entry.crop_id))

    def resolve(self, crop_id: str) -> VerifiedRuntime:
        self.guard(crop_id)
        return self.verify_integrity(crop_id)

    def bundle_presence(self, crop_id: str) -> bool:
        """Check for a complete local contract without claiming integrity."""
        entry = self.registry.get(crop_id)
        if (
            entry.model_status != ModelAvailabilityStatus.FROZEN_RUNTIME_READY
            or not entry.runtime_path
        ):
            return False
        root = (self.project_root / entry.runtime_path).resolve()
        if self.project_root not in root.parents:
            return False
        if any(
            marker in part.casefold()
            for part in root.parts
            for marker in FORBIDDEN_RUNTIME_MARKERS
        ):
            return False
        return root.is_dir() and all(
            (root / name).is_file() for name in REQUIRED_RUNTIME_FILES
        )

    def verify_integrity(self, crop_id: str) -> VerifiedRuntime:
        """Verify a frozen runtime without granting inference authorization."""
        entry = self.registry.get(crop_id)
        if entry.model_status != ModelAvailabilityStatus.FROZEN_RUNTIME_READY:
            raise RuntimeIntegrityError("crop has no frozen runtime to verify")
        if not entry.runtime_path:
            raise RuntimeIntegrityError("runtime path is missing")
        root = (self.project_root / entry.runtime_path).resolve()
        if self.project_root not in root.parents:
            raise RuntimeIntegrityError("runtime path escapes project root")
        for part in root.parts:
            if any(marker in part.casefold() for marker in FORBIDDEN_RUNTIME_MARKERS):
                raise RuntimeIntegrityError("sealed test material is forbidden at runtime")
        missing = [name for name in REQUIRED_RUNTIME_FILES if not (root / name).is_file()]
        if missing:
            logger.error("integrity_failure", extra={"crop_id": entry.crop_id, "category": "missing_file"})
            raise RuntimeIntegrityError(f"required runtime files missing: {', '.join(missing)}")
        expected: dict[str, str] = {}
        for line in (root / "SHA256SUMS.txt").read_text("utf-8").splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            digest, relative = line.split(maxsplit=1)
            relative = relative.strip()
            if Path(relative).name != relative or len(digest) != 64:
                raise RuntimeIntegrityError("invalid SHA256SUMS entry")
            expected[relative] = digest.casefold()
        for name in REQUIRED_RUNTIME_FILES:
            if name == "SHA256SUMS.txt":
                continue
            if expected.get(name) != _sha256(root / name):
                logger.error("integrity_failure", extra={"crop_id": entry.crop_id, "category": "hash_mismatch"})
                raise RuntimeIntegrityError(f"runtime hash mismatch: {name}")
        class_map = json.loads((root / "class_to_index.json").read_text("utf-8"))
        if sorted(class_map.values()) != list(range(len(class_map))):
            raise RuntimeIntegrityError("class map indices are not contiguous")
        runtime = VerifiedRuntime(
            crop_id=entry.crop_id,
            root=root,
            class_to_index=class_map,
            preprocessing=json.loads((root / "preprocessing.json").read_text("utf-8")),
            temperature=json.loads((root / "temperature.json").read_text("utf-8")),
            thresholds=json.loads((root / "selected_thresholds.json").read_text("utf-8")),
            abstention_policy=json.loads((root / "abstention_policy.json").read_text("utf-8")),
        )
        logger.info("runtime_resolved", extra={"crop_id": entry.crop_id})
        return runtime
