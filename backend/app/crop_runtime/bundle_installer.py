from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

EXPECTED_TOP_LEVEL = "deployment_candidate_bundle"
DEPLOYMENT_MANIFEST = "DEPLOYMENT_BUNDLE_SHA256SUMS.txt"
RUNTIME_MANIFEST = "SHA256SUMS.txt"
FINAL_DECISION = "REDGRAM_V2_FINAL_DEPLOYMENT_DECISION.json"


class BundleVerificationError(RuntimeError):
    pass


@dataclass(frozen=True)
class RedgramV2Expectations:
    zip_sha256: str
    checkpoint_sha256: str
    model_name: str
    supported_classes: tuple[str, ...]
    temperature: float
    class_gates: dict[str, dict[str, float]]
    fallback: str
    field_validation_status: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect_archive(archive: Path) -> tuple[zipfile.ZipInfo, ...]:
    with zipfile.ZipFile(archive) as bundle:
        entries = tuple(bundle.infolist())
    if not entries:
        raise BundleVerificationError("archive is empty")
    for entry in entries:
        name = entry.filename.replace("\\", "/")
        parts = PurePosixPath(name).parts
        mode = (entry.external_attr >> 16) & 0xFFFF
        if name.startswith("/") or (len(name) > 1 and name[1] == ":"):
            raise BundleVerificationError("absolute archive path rejected")
        if ".." in parts:
            raise BundleVerificationError("archive traversal rejected")
        if stat.S_ISLNK(mode):
            raise BundleVerificationError("archive symlink rejected")
        if entry.flag_bits & 1:
            raise BundleVerificationError("encrypted archive entry rejected")
        if not parts or parts[0] != EXPECTED_TOP_LEVEL:
            raise BundleVerificationError("file outside expected bundle directory")
    return entries


def _manifest(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise BundleVerificationError(f"missing manifest: {path.name}")
    values: dict[str, str] = {}
    for line in path.read_text("utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            digest, filename = line.split(maxsplit=1)
        except ValueError as exc:
            raise BundleVerificationError("invalid manifest line") from exc
        filename = filename.strip()
        if (
            len(digest) != 64
            or any(ch not in "0123456789abcdef" for ch in digest)
            or Path(filename).name != filename
            or filename in values
        ):
            raise BundleVerificationError("invalid manifest entry")
        values[filename] = digest
    return values


def verify_manifest(root: Path, manifest_name: str) -> dict[str, str]:
    values = _manifest(root / manifest_name)
    for filename, expected in values.items():
        target = root / filename
        if not target.is_file() or sha256_file(target) != expected:
            raise BundleVerificationError(f"manifest mismatch: {filename}")
    return values


def _json(root: Path, filename: str) -> dict:
    try:
        value = json.loads((root / filename).read_text("utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BundleVerificationError(f"invalid JSON: {filename}") from exc
    if not isinstance(value, dict):
        raise BundleVerificationError(f"invalid JSON object: {filename}")
    return value


def _gate_values(raw: dict, classes: tuple[str, ...]) -> dict[str, dict[str, float]]:
    gates = raw.get("class_thresholds")
    if not isinstance(gates, dict) or tuple(gates) != classes:
        raise BundleVerificationError("class gate order mismatch")
    if any(not isinstance(gates.get(name), dict) for name in classes):
        raise BundleVerificationError("invalid class gate")
    return {
        name: {
            "confidence_threshold": gates[name].get("confidence_threshold"),
            "margin_threshold": gates[name].get("margin_threshold"),
        }
        for name in classes
    }


def verify_redgram_v2_bundle(
    root: Path, expected: RedgramV2Expectations
) -> dict[str, object]:
    deployment_hashes = verify_manifest(root, DEPLOYMENT_MANIFEST)
    runtime_hashes = verify_manifest(root, RUNTIME_MANIFEST)
    all_bundle_files = {
        path.name for path in root.iterdir() if path.is_file() and path.name != DEPLOYMENT_MANIFEST
    }
    if set(deployment_hashes) != all_bundle_files:
        raise BundleVerificationError("deployment manifest coverage mismatch")
    expected_runtime_files = {
        "FROZEN_DECISION_RECORD.md",
        "abstention_policy.json",
        "best.pt",
        "class_to_index.json",
        "index_to_class.json",
        "preprocessing.json",
        "runtime_config.json",
        "selected_class_specific_thresholds.json",
        "temperature.json",
    }
    if set(runtime_hashes) != expected_runtime_files:
        raise BundleVerificationError("runtime manifest coverage mismatch")
    if sha256_file(root / "best.pt") != expected.checkpoint_sha256:
        raise BundleVerificationError("checkpoint hash mismatch")

    runtime = _json(root, "runtime_config.json")
    class_map = _json(root, "class_to_index.json")
    temperature = _json(root, "temperature.json")
    thresholds = _json(root, "selected_class_specific_thresholds.json")
    abstention = _json(root, "abstention_policy.json")
    decision = _json(root, FINAL_DECISION)

    ordered_classes = tuple(
        name for name, _ in sorted(class_map.items(), key=lambda item: item[1])
    )
    if runtime.get("model_name") != expected.model_name:
        raise BundleVerificationError("runtime model name mismatch")
    if runtime.get("checkpoint_sha256") != expected.checkpoint_sha256:
        raise BundleVerificationError("runtime checkpoint hash mismatch")
    if ordered_classes != expected.supported_classes:
        raise BundleVerificationError("supported class order mismatch")
    if tuple(runtime.get("supported_classes", ())) != expected.supported_classes:
        raise BundleVerificationError("runtime supported class order mismatch")
    if temperature.get("temperature") != expected.temperature:
        raise BundleVerificationError("temperature mismatch")
    if runtime.get("temperature") != expected.temperature:
        raise BundleVerificationError("runtime temperature mismatch")
    if _gate_values(thresholds, expected.supported_classes) != expected.class_gates:
        raise BundleVerificationError("threshold gate mismatch")
    if _gate_values(abstention, expected.supported_classes) != expected.class_gates:
        raise BundleVerificationError("abstention gate mismatch")
    if abstention.get("fallback_behavior") != expected.fallback:
        raise BundleVerificationError("fallback mismatch")
    if runtime.get("official_accuracy_claim") is not False:
        raise BundleVerificationError("runtime official accuracy claim must be false")
    if decision.get("official_accuracy_claim") is not False:
        raise BundleVerificationError("decision official accuracy claim must be false")
    if decision.get("model_name") != expected.model_name:
        raise BundleVerificationError("decision model name mismatch")
    if decision.get("checkpoint_sha256") != expected.checkpoint_sha256:
        raise BundleVerificationError("decision checkpoint hash mismatch")
    if tuple(decision.get("supported_classes", ())) != expected.supported_classes:
        raise BundleVerificationError("decision supported class order mismatch")
    if decision.get("temperature") != expected.temperature:
        raise BundleVerificationError("decision temperature mismatch")
    if _gate_values(decision, expected.supported_classes) != expected.class_gates:
        raise BundleVerificationError("decision gate mismatch")
    if decision.get("fallback_behavior") != expected.fallback:
        raise BundleVerificationError("decision fallback mismatch")
    if decision.get("field_validation_status") != expected.field_validation_status:
        raise BundleVerificationError("field validation status mismatch")
    if decision.get("disease_detection_enabled") is not False:
        raise BundleVerificationError("farmer inference must remain disabled")
    if decision.get("general_farmer_inference_authorized") is not False:
        raise BundleVerificationError("general farmer inference must remain unauthorized")

    return {
        "deployment_manifest": deployment_hashes,
        "runtime_manifest": runtime_hashes,
        "checkpoint_sha256": expected.checkpoint_sha256,
        "runtime_snapshot_field_validation_status": runtime.get(
            "field_validation_status"
        ),
        "final_field_validation_status": decision.get("field_validation_status"),
    }


def extract_verify_install(
    archive: Path,
    destination: Path,
    expected: RedgramV2Expectations,
) -> tuple[str, dict[str, object]]:
    if sha256_file(archive) != expected.zip_sha256:
        raise BundleVerificationError("deployment ZIP hash mismatch")
    inspect_archive(archive)
    if sha256_file(archive) != expected.zip_sha256:
        raise BundleVerificationError("deployment ZIP changed after inspection")
    destination.parent.mkdir(parents=True, exist_ok=True)
    quarantine_root = destination.parent.parent / "quarantine"
    quarantine_root.mkdir(parents=True, exist_ok=True)
    quarantine = Path(
        tempfile.mkdtemp(prefix="redgram_v2_", dir=quarantine_root)
    )
    try:
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(quarantine)
        candidate = quarantine / EXPECTED_TOP_LEVEL
        report = verify_redgram_v2_bundle(candidate, expected)
        if destination.exists():
            current = {
                str(path.relative_to(destination)): sha256_file(path)
                for path in destination.rglob("*")
                if path.is_file()
            }
            proposed = {
                str(path.relative_to(candidate)): sha256_file(path)
                for path in candidate.rglob("*")
                if path.is_file()
            }
            if current != proposed:
                raise BundleVerificationError("existing runtime conflict")
            return "ALREADY_INSTALLED", report
        os.replace(candidate, destination)
        return "INSTALLED", report
    finally:
        shutil.rmtree(quarantine, ignore_errors=True)
