"""Executable, provenance-bound model promotion gates.

This module validates evidence records but does not pretend that a local JSON
file is a signature.  FARMER decisions require a caller supplied release
control-plane verifier; the CLI deliberately has no such verifier.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from typing import Any, Callable

from .contracts import ContractValidationError, SCHEMA_VERSION, SHA256_RE
from .evaluation import validate_evaluation_report

STAGES = ("OFFLINE_ONLY", "INTERNAL", "KVK_PILOT", "FARMER")
BASE_EVIDENCE = ("dataset_contract_valid", "group_leakage_zero", "sealed_test_policy_valid", "artifact_integrity_valid", "runtime_parity_valid", "rollback_ready")
FIELD_EVIDENCE = ("independent_expert_field_labels", "field_diversity_valid", "reviewer_signoff", "zero_p0_safety_events")
REQUIRED_THRESHOLDS = ("min_accuracy", "min_macro_f1", "min_coverage", "min_accepted_accuracy", "max_accepted_errors", "max_ece_15", "max_ood_false_accept_rate", "max_p95_latency_ms")
POLICY_FIELDS = {"schema_version", "policy_id", "stage", "thresholds", "min_class_recall", "approved_by", "approved_at_utc", "policy_sha256"}
EVIDENCE_FIELDS = {"schema_version", "evidence_id", "checks", "approved_by", "approved_at_utc", "approval_reference", "evidence_sha256"}
ApprovalVerifier = Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], bool]


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_utc(value: Any) -> bool:
    if not _nonempty(value):
        return False
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None
    except ValueError:
        return False


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _fingerprint(payload: dict[str, Any], field: str) -> str:
    value = {key: item for key, item in payload.items() if key != field}
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def validate_promotion_policy(policy: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(policy, dict):
        raise ContractValidationError(["policy:object_required"])
    errors: list[str] = []
    errors.extend(f"policy.{key}:unknown" for key in sorted(set(policy) - POLICY_FIELDS))
    for key in POLICY_FIELDS:
        if key not in policy:
            errors.append(f"policy.{key}:missing")
    if errors:
        raise ContractValidationError(errors)
    if policy["schema_version"] != SCHEMA_VERSION:
        errors.append("policy.schema_version:unsupported")
    if not _nonempty(policy["policy_id"]):
        errors.append("policy.policy_id:nonempty_string_required")
    if policy["stage"] not in STAGES:
        errors.append("policy.stage:unsupported")
    if not _nonempty(policy["approved_by"]):
        errors.append("policy.approved_by:nonempty_string_required")
    if not _valid_utc(policy["approved_at_utc"]):
        errors.append("policy.approved_at_utc:timezone_required")
    thresholds = policy["thresholds"]
    if not isinstance(thresholds, dict) or set(thresholds) != set(REQUIRED_THRESHOLDS):
        errors.append("policy.thresholds:closed_required_contract")
    else:
        for name in REQUIRED_THRESHOLDS:
            value = thresholds[name]
            if not _number(value):
                errors.append(f"policy.thresholds.{name}:numeric_required")
        for name in ("min_accuracy", "min_macro_f1", "min_coverage", "min_accepted_accuracy", "max_ece_15", "max_ood_false_accept_rate"):
            value = thresholds[name]
            if _number(value) and not 0 <= value <= 1:
                errors.append(f"policy.thresholds.{name}:must_be_0_to_1")
        value = thresholds["max_accepted_errors"]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            errors.append("policy.thresholds.max_accepted_errors:non_negative_integer_required")
        value = thresholds["max_p95_latency_ms"]
        if _number(value) and value <= 0:
            errors.append("policy.thresholds.max_p95_latency_ms:must_be_positive")
    recalls = policy["min_class_recall"]
    if not isinstance(recalls, dict) or not recalls:
        errors.append("policy.min_class_recall:non_empty_object_required")
    else:
        for label, value in recalls.items():
            if not _nonempty(label) or not _number(value) or not 0 <= value <= 1:
                errors.append(f"policy.min_class_recall.{label}:must_be_finite_0_to_1")
    digest = policy["policy_sha256"]
    if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
        errors.append("policy.policy_sha256:invalid")
    elif digest != _fingerprint(policy, "policy_sha256"):
        errors.append("policy.policy_sha256:mismatch")
    if errors:
        raise ContractValidationError(errors)
    return dict(policy)


def validate_promotion_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(evidence, dict):
        raise ContractValidationError(["evidence:object_required"])
    errors: list[str] = []
    errors.extend(f"evidence.{key}:unknown" for key in sorted(set(evidence) - EVIDENCE_FIELDS))
    for key in EVIDENCE_FIELDS:
        if key not in evidence:
            errors.append(f"evidence.{key}:missing")
    if errors:
        raise ContractValidationError(errors)
    if evidence["schema_version"] != SCHEMA_VERSION:
        errors.append("evidence.schema_version:unsupported")
    for key in ("evidence_id", "approved_by", "approval_reference"):
        if not _nonempty(evidence[key]):
            errors.append(f"evidence.{key}:nonempty_string_required")
    if not _valid_utc(evidence["approved_at_utc"]):
        errors.append("evidence.approved_at_utc:timezone_required")
    checks = evidence["checks"]
    allowed_checks = set(BASE_EVIDENCE) | set(FIELD_EVIDENCE)
    if not isinstance(checks, dict) or any(key not in allowed_checks for key in checks) or any(not isinstance(value, bool) for value in checks.values()):
        errors.append("evidence.checks:boolean_allowlist_map_required")
    digest = evidence["evidence_sha256"]
    if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
        errors.append("evidence.evidence_sha256:invalid")
    elif digest != _fingerprint(evidence, "evidence_sha256"):
        errors.append("evidence.evidence_sha256:mismatch")
    if errors:
        raise ContractValidationError(errors)
    return dict(evidence)


def _gate(name: str, actual: float | int | None, threshold: float | int, direction: str) -> dict[str, Any]:
    passed = actual is not None and _number(actual) and (actual >= threshold if direction == "min" else actual <= threshold)
    return {"name": name, "actual": actual, "threshold": threshold, "direction": direction, "passed": passed}


def evaluate_promotion(evaluation: dict[str, Any], policy: dict[str, Any], evidence: dict[str, Any], *, approval_verifier: ApprovalVerifier | None = None) -> dict[str, Any]:
    """Evaluate explicit gates; farmer enablement needs external verification."""
    evaluation = validate_evaluation_report(evaluation)
    policy = validate_promotion_policy(policy)
    evidence = validate_promotion_evidence(evidence)
    lineage = evaluation["lineage"]
    if lineage["policy_sha256"] != policy["policy_sha256"]:
        raise ContractValidationError(["promotion.policy_sha256:does_not_match_evaluation_lineage"])
    metrics = evaluation["metrics"]
    selection = metrics["selection"]
    calibration = metrics["calibration"]
    ood = metrics["ood"]
    latency = metrics["latency_ms"]
    thresholds = policy["thresholds"]
    gates = [
        _gate("accuracy", metrics.get("accuracy"), thresholds["min_accuracy"], "min"),
        _gate("macro_f1", metrics.get("macro_f1"), thresholds["min_macro_f1"], "min"),
        _gate("coverage", selection.get("coverage"), thresholds["min_coverage"], "min"),
        _gate("accepted_accuracy", selection.get("accepted_accuracy"), thresholds["min_accepted_accuracy"], "min"),
        _gate("accepted_errors", selection.get("accepted_errors"), thresholds["max_accepted_errors"], "max"),
        _gate("ece_15", calibration.get("ece_15"), thresholds["max_ece_15"], "max"),
        _gate("ood_false_accept_rate", ood.get("false_accept_rate"), thresholds["max_ood_false_accept_rate"], "max"),
        _gate("p95_latency_ms", latency.get("p95"), thresholds["max_p95_latency_ms"], "max"),
    ]
    per_class = metrics["per_class"]
    for label, threshold in sorted(policy["min_class_recall"].items()):
        gates.append(_gate(f"class_recall:{label}", per_class.get(label, {}).get("recall"), threshold, "min"))
    evidence_names = list(BASE_EVIDENCE)
    if policy["stage"] == "FARMER":
        evidence_names.extend(FIELD_EVIDENCE)
    evidence_gates = [{"name": name, "actual": evidence["checks"].get(name), "expected": True, "passed": evidence["checks"].get(name) is True} for name in evidence_names]
    approval_verified = False
    if policy["stage"] == "FARMER" and approval_verifier is not None:
        try:
            approval_verified = approval_verifier(evaluation, policy, evidence) is True
        except Exception:
            approval_verified = False
    if policy["stage"] == "FARMER":
        evidence_gates.append({"name": "external_release_approval_verified", "actual": approval_verified, "expected": True, "passed": approval_verified})
    passed = all(gate["passed"] for gate in gates + evidence_gates)
    decision = {
        "schema_version": SCHEMA_VERSION, "stage": policy["stage"], "model_version": lineage["model_version"],
        "artifact_sha256": lineage["artifact_sha256"], "policy_sha256": policy["policy_sha256"],
        "evaluation_report_sha256": evaluation["report_sha256"], "evidence_sha256": evidence["evidence_sha256"],
        "passed": passed, "farmer_inference_enabled": passed and policy["stage"] == "FARMER",
        "metric_gates": gates, "evidence_gates": evidence_gates,
        "reason_codes": [f"GATE_FAILED:{gate['name']}" for gate in gates + evidence_gates if not gate["passed"]],
    }
    decision["decision_sha256"] = _fingerprint(decision, "decision_sha256")
    return decision
