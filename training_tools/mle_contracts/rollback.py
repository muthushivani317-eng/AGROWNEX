"""Validated registry with a hash-chained audit trail and rollback drill.

The hash chain detects accidental or unauthorised edits only when a trusted
copy of the latest digest is retained by the release control plane.  It is not
a signature and does not replace write access control.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .contracts import ContractValidationError, SCHEMA_VERSION, SHA256_RE

REGISTRY_FIELDS = {"schema_version", "crops", "audit"}
ENTRY_FIELDS = {"current", "previous", "candidate", "enabled"}
AUDIT_FIELDS = {"timestamp_utc", "crop", "action", "detail", "previous_event_sha256", "event_sha256"}
DECISION_FIELDS = {"schema_version", "stage", "model_version", "artifact_sha256", "policy_sha256", "evaluation_report_sha256", "evidence_sha256", "passed", "farmer_inference_enabled", "metric_gates", "evidence_gates", "reason_codes", "decision_sha256"}


def _valid_utc(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None
    except ValueError:
        return False


def _canonical_hash(payload: dict[str, Any], digest_field: str) -> str:
    value = {key: item for key, item in payload.items() if key != digest_field}
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _validate_artifact(reference: Any, prefix: str) -> None:
    if not isinstance(reference, dict):
        raise ContractValidationError([f"{prefix}:object_required"])
    errors = [f"{prefix}.{key}:unknown" for key in sorted(set(reference) - {"model_version", "artifact_sha256", "policy_sha256"})]
    if not isinstance(reference.get("model_version"), str) or not reference["model_version"].strip():
        errors.append(f"{prefix}.model_version:missing")
    for field in ("artifact_sha256", "policy_sha256"):
        value = reference.get(field)
        if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
            errors.append(f"{prefix}.{field}:invalid")
    if errors:
        raise ContractValidationError(errors)


def _validate_decision(decision: Any) -> None:
    if not isinstance(decision, dict):
        raise ContractValidationError(["promotion_decision:object_required"])
    errors = [f"promotion_decision.{key}:unknown" for key in sorted(set(decision) - DECISION_FIELDS)]
    for key in DECISION_FIELDS:
        if key not in decision:
            errors.append(f"promotion_decision.{key}:missing")
    if errors:
        raise ContractValidationError(errors)
    if decision["schema_version"] != SCHEMA_VERSION or decision["passed"] is not True:
        errors.append("promotion_decision:not_passed_or_unsupported")
    for field in ("model_version",):
        if not isinstance(decision[field], str) or not decision[field].strip():
            errors.append(f"promotion_decision.{field}:invalid")
    for field in ("artifact_sha256", "policy_sha256", "evaluation_report_sha256", "evidence_sha256", "decision_sha256"):
        if not isinstance(decision[field], str) or not SHA256_RE.fullmatch(decision[field]):
            errors.append(f"promotion_decision.{field}:invalid")
    if decision.get("decision_sha256") != _canonical_hash(decision, "decision_sha256"):
        errors.append("promotion_decision:integrity_mismatch")
    if errors:
        raise ContractValidationError(errors)


def _validate_state(state: Any) -> None:
    if not isinstance(state, dict):
        raise ContractValidationError(["registry:object_required"])
    errors = [f"registry.{key}:unknown" for key in sorted(set(state) - REGISTRY_FIELDS)]
    for key in REGISTRY_FIELDS:
        if key not in state:
            errors.append(f"registry.{key}:missing")
    if errors:
        raise ContractValidationError(errors)
    if state["schema_version"] != SCHEMA_VERSION:
        errors.append("registry.schema_version:unsupported")
    if not isinstance(state["crops"], dict):
        errors.append("registry.crops:object_required")
    else:
        for crop, entry in state["crops"].items():
            if not isinstance(crop, str) or not crop.strip():
                errors.append("registry.crops:nonempty_crop_required")
            if not isinstance(entry, dict) or set(entry) != ENTRY_FIELDS:
                errors.append(f"registry.crops.{crop}:closed_entry_required")
                continue
            try:
                _validate_artifact(entry["current"], f"registry.crops.{crop}.current")
                for field in ("previous", "candidate"):
                    if entry[field] is not None:
                        _validate_artifact(entry[field], f"registry.crops.{crop}.{field}")
                if not isinstance(entry["enabled"], bool):
                    errors.append(f"registry.crops.{crop}.enabled:boolean_required")
            except ContractValidationError as exc:
                errors.extend(exc.errors)
    audit = state["audit"]
    if not isinstance(audit, list):
        errors.append("registry.audit:array_required")
    else:
        previous: str | None = None
        for index, event in enumerate(audit):
            prefix = f"registry.audit[{index}]"
            if not isinstance(event, dict) or set(event) != AUDIT_FIELDS:
                errors.append(f"{prefix}:closed_event_required")
                continue
            if not _valid_utc(event["timestamp_utc"]):
                errors.append(f"{prefix}.timestamp_utc:invalid")
            if not isinstance(event["crop"], str) or not event["crop"].strip() or not isinstance(event["action"], str) or not event["action"].strip() or not isinstance(event["detail"], str):
                errors.append(f"{prefix}:invalid_fields")
            if event["previous_event_sha256"] != previous:
                errors.append(f"{prefix}.previous_event_sha256:mismatch")
            digest = event["event_sha256"]
            if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest) or digest != _canonical_hash(event, "event_sha256"):
                errors.append(f"{prefix}.event_sha256:mismatch")
            previous = digest if isinstance(digest, str) else None
    if errors:
        raise ContractValidationError(errors)


class ModelRegistry:
    """Crop-scoped registry whose transitions are checked and audit-chained."""

    def __init__(self, state: dict[str, Any] | None = None):
        self.state = copy.deepcopy(state or {"schema_version": SCHEMA_VERSION, "crops": {}, "audit": []})
        _validate_state(self.state)

    def register_current(self, crop: str, artifact: dict[str, Any], *, enabled: bool = False) -> None:
        if not isinstance(crop, str) or not crop.strip():
            raise ContractValidationError(["crop:nonempty_string_required"])
        _validate_artifact(artifact, "artifact")
        if crop in self.state["crops"]:
            raise ContractValidationError([f"crop:{crop}:already_registered"])
        self.state["crops"][crop] = {"current": copy.deepcopy(artifact), "previous": None, "candidate": None, "enabled": bool(enabled)}
        self._audit(crop, "REGISTER_CURRENT", artifact["model_version"])

    def set_candidate(self, crop: str, artifact: dict[str, Any]) -> None:
        _validate_artifact(artifact, "candidate")
        entry = self._entry(crop)
        entry["candidate"] = copy.deepcopy(artifact)
        self._audit(crop, "SET_CANDIDATE", artifact["model_version"])

    def promote(self, crop: str, decision: dict[str, Any]) -> None:
        entry = self._entry(crop)
        candidate = entry.get("candidate")
        if candidate is None:
            raise ContractValidationError([f"crop:{crop}:candidate_missing"])
        _validate_decision(decision)
        for field in ("model_version", "artifact_sha256", "policy_sha256"):
            if decision[field] != candidate[field]:
                raise ContractValidationError([f"promotion_decision:{field}_mismatch_candidate"])
        entry["previous"] = entry["current"]
        entry["current"] = candidate
        entry["candidate"] = None
        entry["enabled"] = decision["farmer_inference_enabled"] is True
        self._audit(crop, "PROMOTE", entry["current"]["model_version"])

    def rollback(self, crop: str, *, trigger: str) -> None:
        if not isinstance(trigger, str) or not trigger.strip():
            raise ContractValidationError(["rollback.trigger:nonempty_string_required"])
        entry = self._entry(crop)
        previous = entry.get("previous")
        if previous is None:
            entry["enabled"] = False
            self._audit(crop, "DISABLE_NO_PREVIOUS", trigger)
            return
        failed = entry["current"]
        entry["current"] = previous
        entry["previous"] = None
        entry["candidate"] = failed
        entry["enabled"] = False
        self._audit(crop, "ROLLBACK", trigger)

    def save_atomic(self, path: Path) -> None:
        _validate_state(self.state)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            handle.write(json.dumps(self.state, indent=2, sort_keys=True, allow_nan=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)

    def _entry(self, crop: str) -> dict[str, Any]:
        try:
            return self.state["crops"][crop]
        except KeyError as exc:
            raise ContractValidationError([f"crop:{crop}:not_registered"]) from exc

    def _audit(self, crop: str, action: str, detail: str) -> None:
        previous = self.state["audit"][-1]["event_sha256"] if self.state["audit"] else None
        event = {"timestamp_utc": datetime.now(UTC).isoformat(), "crop": crop, "action": action, "detail": detail, "previous_event_sha256": previous}
        event["event_sha256"] = _canonical_hash(event, "event_sha256")
        self.state["audit"].append(event)


def execute_rollback_drill(state: dict[str, Any], crop: str, *, trigger: str = "SIMULATED_ARTIFACT_INTEGRITY_FAILURE") -> dict[str, Any]:
    """Exercise in-memory rollback evidence only; it does not test serving traffic."""
    registry = ModelRegistry(state)
    before = copy.deepcopy(registry.state["crops"].get(crop))
    if before is None:
        raise ContractValidationError([f"crop:{crop}:not_registered"])
    registry.rollback(crop, trigger=trigger)
    after = registry.state["crops"][crop]
    restored = before.get("previous") is not None and after["current"] == before["previous"]
    disabled_safely = before.get("previous") is None and after["enabled"] is False
    return {"schema_version": SCHEMA_VERSION, "crop": crop, "trigger": trigger, "passed": restored or disabled_safely, "restored_previous": restored, "disabled_without_previous": disabled_safely, "before": before, "after": after, "audit_event": registry.state["audit"][-1], "limitations": "In-memory state-transition drill only; it does not verify persisted registry reload, model loading, traffic disablement, or backend readiness."}
