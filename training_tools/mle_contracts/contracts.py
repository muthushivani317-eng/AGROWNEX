"""Strict, dependency-free validation for governed ML evidence contracts.

The JSON schemas in ``docs/model_contracts`` are the public interchange
contracts.  These validators deliberately enforce the same closed shapes at
runtime so a caller cannot bypass the schema by invoking Python directly.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Iterable

SCHEMA_VERSION = "1.0.0"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DATASET_ROLES = {
    "training",
    "development_validation",
    "calibration",
    "sealed_field_test",
}
GROUP_FIELDS = (
    "source_group_id",
    "farm_id",
    "visit_id",
    "plant_id",
    "leaf_id",
    "capture_group_id",
    "duplicate_family_id",
)
ROW_FIELDS = (
    "image_id",
    "sha256",
    "crop_id",
    "canonical_class",
    "dataset_role",
    "source_id",
    "source_group_id",
    "licence_status",
    "consent_for_training",
    "consent_for_sealed_testing",
    "expert_review_status",
    "quality_status",
    "privacy_status",
    *GROUP_FIELDS[1:],
)
OPTIONAL_ROW_FIELDS = {
    "district_code",
    "device_family",
    "view_type",
    "growth_stage",
    "symptom_stage",
}
MANIFEST_FIELDS = {
    "schema_version",
    "dataset_id",
    "snapshot_id",
    "taxonomy_version",
    "created_at_utc",
    "dataset_sha256",
    "rows",
}
EVENT_FIELDS = (
    "schema_version",
    "prediction_request_id",
    "timestamp_utc",
    "crop_id",
    "model_version",
    "artifact_sha256",
    "policy_sha256",
    "decision_code",
    "outcome",
    "confidence",
    "margin",
    "latency_ms",
)
OPTIONAL_EVENT_FIELDS = {
    "predicted_class",
    "image_retention_consent",
    "image_reference",
    "review_id",
}
FORBIDDEN_EVENT_FIELDS = {
    "phone",
    "phone_number",
    "email",
    "token",
    "access_token",
    "refresh_token",
    "farmer_name",
    "latitude",
    "longitude",
    "raw_image",
    "image_bytes",
}


class ContractValidationError(ValueError):
    """Raised when governed ML evidence does not satisfy its contract."""

    def __init__(self, errors: Iterable[str]):
        self.errors = tuple(errors)
        super().__init__("; ".join(self.errors))


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _valid_utc(value: Any) -> bool:
    if not _nonempty_string(value):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _canonical_sha256(payload: dict[str, Any], digest_field: str) -> str:
    unhashed = {key: value for key, value in payload.items() if key != digest_field}
    return hashlib.sha256(
        json.dumps(unhashed, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def dataset_fingerprint(manifest: dict[str, Any]) -> str:
    """Hash semantic manifest content using stable JSON serialization."""
    return _canonical_sha256(manifest, "dataset_sha256")


def validate_dataset_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Validate provenance, eligibility, deduplication, and group isolation."""
    errors: list[str] = []
    if not isinstance(manifest, dict):
        raise ContractValidationError(["manifest:object_required"])
    extra = sorted(set(manifest) - MANIFEST_FIELDS)
    errors.extend(f"manifest.{field}:unknown" for field in extra)
    required = ("schema_version", "dataset_id", "snapshot_id", "taxonomy_version", "created_at_utc", "rows")
    for key in required:
        if key not in manifest:
            errors.append(f"manifest.{key}:missing")
    if any(key not in manifest for key in required):
        raise ContractValidationError(errors)
    if manifest["schema_version"] != SCHEMA_VERSION:
        errors.append("manifest.schema_version:unsupported")
    for key in ("dataset_id", "snapshot_id", "taxonomy_version"):
        if not _nonempty_string(manifest[key]):
            errors.append(f"manifest.{key}:nonempty_string_required")
    if not _valid_utc(manifest["created_at_utc"]):
        errors.append("manifest.created_at_utc:timezone_required")
    rows = manifest["rows"]
    if not isinstance(rows, list) or not rows:
        errors.append("manifest.rows:non_empty_array_required")
        raise ContractValidationError(errors)

    ids: set[str] = set()
    hashes: dict[str, set[str]] = defaultdict(set)
    groups: dict[str, dict[str, set[str]]] = {field: defaultdict(set) for field in GROUP_FIELDS}
    for index, row in enumerate(rows):
        prefix = f"rows[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{prefix}:object_required")
            continue
        extra_row = sorted(set(row) - set(ROW_FIELDS) - OPTIONAL_ROW_FIELDS)
        errors.extend(f"{prefix}.{field}:unknown" for field in extra_row)
        for field in ROW_FIELDS:
            if field not in row:
                errors.append(f"{prefix}.{field}:missing")
        if any(field not in row for field in ROW_FIELDS):
            continue
        for field in ("image_id", "crop_id", "canonical_class", "source_id", *GROUP_FIELDS):
            if not _nonempty_string(row[field]):
                errors.append(f"{prefix}.{field}:nonempty_string_required")
        for field in OPTIONAL_ROW_FIELDS:
            if field in row and row[field] is not None and not _nonempty_string(row[field]):
                errors.append(f"{prefix}.{field}:string_or_null_required")
        image_id = row["image_id"]
        if _nonempty_string(image_id):
            if image_id in ids:
                errors.append(f"{prefix}.image_id:duplicate:{image_id}")
            ids.add(image_id)
        digest = row["sha256"]
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            errors.append(f"{prefix}.sha256:invalid")
        role = row["dataset_role"]
        if role not in DATASET_ROLES:
            errors.append(f"{prefix}.dataset_role:unsupported:{role}")
            continue
        if isinstance(digest, str) and SHA256_RE.fullmatch(digest):
            hashes[digest].add(role)
        for field in GROUP_FIELDS:
            if _nonempty_string(row[field]):
                groups[field][row[field]].add(role)
        if row["licence_status"] != "APPROVED":
            errors.append(f"{prefix}.licence_status:not_approved")
        if not isinstance(row["consent_for_training"], bool):
            errors.append(f"{prefix}.consent_for_training:boolean_required")
        if not isinstance(row["consent_for_sealed_testing"], bool):
            errors.append(f"{prefix}.consent_for_sealed_testing:boolean_required")
        if role == "sealed_field_test":
            if row["consent_for_sealed_testing"] is not True:
                errors.append(f"{prefix}.consent_for_sealed_testing:not_true")
        elif row["consent_for_training"] is not True:
            errors.append(f"{prefix}.consent_for_training:not_true")
        if row["expert_review_status"] != "EXPERT_CONFIRMED":
            errors.append(f"{prefix}.expert_review_status:not_confirmed")
        if row["quality_status"] not in {"PASS", "PASS_WITH_WARNING"}:
            errors.append(f"{prefix}.quality_status:not_eligible")
        if row["privacy_status"] != "APPROVED":
            errors.append(f"{prefix}.privacy_status:not_approved")

    for digest, roles in hashes.items():
        occurrences = sum(1 for row in rows if row.get("sha256") == digest)
        if occurrences > 1:
            errors.append(f"sha256:duplicate:{digest}")
        if len(roles) > 1:
            errors.append(f"sha256:cross_role_leakage:{digest}:{sorted(roles)}")
    for field, values in groups.items():
        for value, roles in values.items():
            if len(roles) > 1:
                errors.append(f"{field}:cross_role_leakage:{value}:{sorted(roles)}")
    supplied = manifest.get("dataset_sha256")
    if supplied is not None and (not isinstance(supplied, str) or not SHA256_RE.fullmatch(supplied)):
        errors.append("manifest.dataset_sha256:invalid")
    computed = dataset_fingerprint(manifest)
    if supplied is not None and supplied != computed:
        errors.append("manifest.dataset_sha256:mismatch")
    if errors:
        raise ContractValidationError(errors)
    return {
        "valid": True,
        "row_count": len(rows),
        "roles": {role: sum(row["dataset_role"] == role for row in rows) for role in sorted(DATASET_ROLES)},
        "dataset_sha256": computed,
        "group_fields_checked": list(GROUP_FIELDS),
    }


def validate_prediction_event(event: dict[str, Any]) -> dict[str, Any]:
    """Validate a closed, privacy-minimized prediction event."""
    if not isinstance(event, dict):
        raise ContractValidationError(["event:object_required"])
    errors: list[str] = []
    missing = [f"event.{field}:missing" for field in EVENT_FIELDS if field not in event]
    errors.extend(missing)
    forbidden = sorted(FORBIDDEN_EVENT_FIELDS.intersection(event))
    errors.extend(f"event.{field}:forbidden" for field in forbidden)
    extra = sorted(set(event) - set(EVENT_FIELDS) - OPTIONAL_EVENT_FIELDS)
    errors.extend(f"event.{field}:unknown" for field in extra if field not in FORBIDDEN_EVENT_FIELDS)
    if missing:
        raise ContractValidationError(errors)
    if event["schema_version"] != SCHEMA_VERSION:
        errors.append("event.schema_version:unsupported")
    for field in ("prediction_request_id", "crop_id", "model_version", "decision_code"):
        if not _nonempty_string(event[field]):
            errors.append(f"event.{field}:nonempty_string_required")
    if not _valid_utc(event["timestamp_utc"]):
        errors.append("event.timestamp_utc:timezone_required")
    for field in ("artifact_sha256", "policy_sha256"):
        if not isinstance(event[field], str) or not SHA256_RE.fullmatch(event[field]):
            errors.append(f"event.{field}:invalid")
    if event["outcome"] not in {"accepted", "abstained", "ood_rejected", "quality_rejected", "error"}:
        errors.append("event.outcome:unsupported")
    for field in ("confidence", "margin"):
        if not _finite_number(event[field]) or not 0 <= event[field] <= 1:
            errors.append(f"event.{field}:must_be_finite_0_to_1")
    if not _finite_number(event["latency_ms"]) or event["latency_ms"] < 0:
        errors.append("event.latency_ms:must_be_non_negative")
    for field in ("predicted_class", "review_id"):
        if field in event and event[field] is not None and not _nonempty_string(event[field]):
            errors.append(f"event.{field}:string_or_null_required")
    if "image_reference" in event and event["image_reference"] is not None and not _nonempty_string(event["image_reference"]):
        errors.append("event.image_reference:string_or_null_required")
    if "image_retention_consent" in event and not isinstance(event["image_retention_consent"], bool):
        errors.append("event.image_retention_consent:boolean_required")
    if event.get("image_reference") is not None and event.get("image_retention_consent") is not True:
        errors.append("event.image_reference:consent_required")
    if errors:
        raise ContractValidationError(errors)
    return dict(event)
