from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from training_tools.mle_contracts import (
    ContractValidationError,
    ModelRegistry,
    build_evaluation_report,
    evaluate_promotion,
    execute_rollback_drill,
    validate_dataset_manifest,
    validate_evaluation_report,
    validate_prediction_event,
    validate_promotion_evidence,
    validate_promotion_policy,
)

HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
SCHEMA_ROOT = Path(__file__).resolve().parents[2] / "docs" / "model_contracts"


def _digest(payload: dict, field: str) -> str:
    return hashlib.sha256(json.dumps({key: value for key, value in payload.items() if key != field}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _row(image_id: str, role: str, suffix: str) -> dict:
    return {
        "image_id": image_id, "sha256": suffix[0] * 64, "crop_id": "banana", "canonical_class": "banana__healthy",
        "dataset_role": role, "source_id": f"source-{suffix}", "source_group_id": f"source-group-{suffix}",
        "licence_status": "APPROVED", "consent_for_training": True, "consent_for_sealed_testing": True,
        "expert_review_status": "EXPERT_CONFIRMED", "quality_status": "PASS", "privacy_status": "APPROVED",
        "farm_id": f"farm-{suffix}", "visit_id": f"visit-{suffix}", "plant_id": f"plant-{suffix}",
        "leaf_id": f"leaf-{suffix}", "capture_group_id": f"capture-{suffix}", "duplicate_family_id": f"duplicate-{suffix}",
    }


def _manifest() -> dict:
    return {"schema_version": "1.0.0", "dataset_id": "banana-field-v1", "snapshot_id": "2026-08-13", "taxonomy_version": "banana-v3", "created_at_utc": "2026-08-13T10:00:00Z", "rows": [_row("one", "training", "a"), _row("two", "sealed_field_test", "b")]}


def _records() -> list[dict]:
    return [
        {"sample_id": "1", "true_label": "healthy", "probabilities": {"healthy": 0.9, "disease": 0.1}, "accepted": True, "is_ood": False, "latency_ms": 10, "evaluation_group_id": "farm-a", "slices": {"device": "a"}},
        {"sample_id": "2", "true_label": "disease", "probabilities": {"healthy": 0.2, "disease": 0.8}, "accepted": True, "is_ood": False, "latency_ms": 20, "evaluation_group_id": "farm-b", "slices": {"device": "b"}},
        {"sample_id": "3", "true_label": "disease", "probabilities": {"healthy": 0.6, "disease": 0.4}, "accepted": False, "is_ood": False, "latency_ms": 30, "evaluation_group_id": "farm-c", "slices": {"device": "b"}},
        {"sample_id": "4", "true_label": "healthy", "probabilities": {"healthy": 0.7, "disease": 0.3}, "accepted": True, "is_ood": False, "latency_ms": 40, "evaluation_group_id": "farm-d", "slices": {"device": "a"}},
        {"sample_id": "ood-1", "true_label": None, "probabilities": {"healthy": 0.6, "disease": 0.4}, "accepted": False, "is_ood": True, "latency_ms": 50, "evaluation_group_id": "ood-source", "slices": {"device": "x"}},
    ]


def _policy(stage: str = "INTERNAL") -> dict:
    value = {
        "schema_version": "1.0.0", "policy_id": "banana-internal-v1", "stage": stage, "approved_by": "plant-pathology-owner",
        "approved_at_utc": "2026-08-13T10:00:00Z",
        "thresholds": {"min_accuracy": 0.7, "min_macro_f1": 0.7, "min_coverage": 0.7, "min_accepted_accuracy": 0.9, "max_accepted_errors": 0, "max_ece_15": 0.5, "max_ood_false_accept_rate": 0.0, "max_p95_latency_ms": 50},
        "min_class_recall": {"healthy": 0.9, "disease": 0.5},
    }
    value["policy_sha256"] = _digest(value, "policy_sha256")
    return value


def _evidence() -> dict:
    value = {
        "schema_version": "1.0.0", "evidence_id": "banana-evidence-v1", "approved_by": "kvk-reviewer",
        "approved_at_utc": "2026-08-13T10:00:00Z", "approval_reference": "kvk-case-17",
        "checks": {"dataset_contract_valid": True, "group_leakage_zero": True, "sealed_test_policy_valid": True, "artifact_integrity_valid": True, "runtime_parity_valid": True, "rollback_ready": True, "independent_expert_field_labels": True, "field_diversity_valid": True, "reviewer_signoff": True, "zero_p0_safety_events": True},
    }
    value["evidence_sha256"] = _digest(value, "evidence_sha256")
    return value


def _report(policy: dict | None = None) -> dict:
    policy = policy or _policy()
    return build_evaluation_report(_records(), ["healthy", "disease"], {"model_version": "candidate-v1", "artifact_sha256": HASH_A, "policy_sha256": policy["policy_sha256"], "dataset_sha256": HASH_C, "code_sha": "deadbeef"}, bootstrap_iterations=25, seed=7)


def _artifact(version: str, digest: str, policy_sha: str) -> dict:
    return {"model_version": version, "artifact_sha256": digest, "policy_sha256": policy_sha}


def _schema(name: str) -> Draft202012Validator:
    return Draft202012Validator(json.loads((SCHEMA_ROOT / name).read_text(encoding="utf-8")))


def test_machine_readable_contract_files_are_valid_and_generated_inputs_conform():
    names = {"disease_dataset_manifest.schema.json", "disease_prediction_event.schema.json", "disease_evaluation_report.schema.json", "disease_promotion_policy.schema.json", "disease_promotion_evidence.schema.json", "disease_model_registry.schema.json"}
    for name in names:
        assert json.loads((SCHEMA_ROOT / name).read_text(encoding="utf-8"))["$schema"].endswith("2020-12/schema")
    event = {"schema_version": "1.0.0", "prediction_request_id": "request-1", "timestamp_utc": "2026-08-13T10:00:00Z", "crop_id": "banana", "model_version": "v1", "artifact_sha256": HASH_A, "policy_sha256": HASH_B, "decision_code": "ACCEPTED", "outcome": "accepted", "confidence": 0.9, "margin": 0.8, "latency_ms": 22}
    registry = ModelRegistry()
    registry.register_current("banana", _artifact("stable-v1", HASH_A, _policy()["policy_sha256"]))
    for name, value in {"disease_dataset_manifest.schema.json": _manifest(), "disease_prediction_event.schema.json": event, "disease_evaluation_report.schema.json": _report(), "disease_promotion_policy.schema.json": _policy(), "disease_promotion_evidence.schema.json": _evidence(), "disease_model_registry.schema.json": registry.state}.items():
        assert not list(_schema(name).iter_errors(value)), name


def test_dataset_contract_rejects_duplicate_bytes_even_in_same_role_and_unknown_fields():
    manifest = _manifest()
    duplicate = _row("three", "training", "c")
    duplicate["sha256"] = manifest["rows"][0]["sha256"]
    manifest["rows"].append(duplicate)
    manifest["surprise"] = "unsafe"
    with pytest.raises(ContractValidationError) as exc:
        validate_dataset_manifest(manifest)
    assert "sha256:duplicate" in str(exc.value)
    assert "manifest.surprise:unknown" in str(exc.value)


def test_dataset_contract_rejects_every_cross_role_group():
    for field in ("source_group_id", "farm_id", "visit_id", "plant_id", "leaf_id", "capture_group_id", "duplicate_family_id"):
        manifest = _manifest()
        manifest["rows"][1][field] = manifest["rows"][0][field]
        with pytest.raises(ContractValidationError, match=field):
            validate_dataset_manifest(manifest)


def test_prediction_event_closed_shape_blocks_pii_invalid_identifiers_and_booleans():
    event = {"schema_version": "wrong", "prediction_request_id": None, "timestamp_utc": "2026-08-13T10:00:00Z", "crop_id": None, "model_version": None, "artifact_sha256": HASH_A, "policy_sha256": HASH_B, "decision_code": None, "outcome": "accepted", "confidence": True, "margin": False, "latency_ms": True, "metadata": {"phone": "+910000000000"}}
    with pytest.raises(ContractValidationError) as exc:
        validate_prediction_event(event)
    message = str(exc.value)
    assert "metadata:unknown" in message
    assert "schema_version:unsupported" in message
    assert "confidence:must_be_finite_0_to_1" in message


def test_evaluation_rejects_duplicate_ids_invalid_ood_and_missing_group():
    records = _records()
    records[1]["sample_id"] = records[0]["sample_id"]
    records[2].pop("evaluation_group_id")
    records[4]["true_label"] = "healthy"
    records[0]["probabilities"] = {"healthy": True, "disease": False}
    with pytest.raises(ContractValidationError) as exc:
        _report() if False else build_evaluation_report(records, ["healthy", "disease"], {"model_version": "candidate-v1", "artifact_sha256": HASH_A, "policy_sha256": _policy()["policy_sha256"], "dataset_sha256": HASH_C, "code_sha": "deadbeef"})
    message = str(exc.value)
    assert "sample_id:duplicate" in message
    assert "evaluation_group_id:missing" in message
    assert "true_label:must_be_null_for_ood" in message
    assert "probabilities:invalid" in message


def test_evaluation_separates_ood_and_uses_cluster_bootstrap_deterministically():
    first = _report()
    second = _report()
    metrics = first["metrics"]
    assert metrics["sample_count"] == 4
    assert metrics["accuracy"] == 0.75
    assert metrics["selection"]["coverage"] == 0.75
    assert metrics["selection"]["accepted_accuracy"] == 1.0
    assert metrics["ood"] == {"sample_count": 1, "false_accept_count": 0, "false_accept_rate": 0.0}
    assert metrics["latency_ms"]["p95"] == pytest.approx(38.5)
    assert first["slices"]["device"]["a"]["id_metrics"]["accuracy"] == 1.0
    assert first["bootstrap"]["method"] == "cluster_bootstrap"
    assert first["metrics"]["confidence_intervals"] == second["metrics"]["confidence_intervals"]
    assert first["report_sha256"] == second["report_sha256"]


def test_evaluation_hash_is_recomputed_and_tampering_is_rejected():
    report = _report()
    report["metrics"]["accuracy"] = 1.0
    with pytest.raises(ContractValidationError, match="report_sha256:mismatch"):
        validate_evaluation_report(report)


def test_promotion_requires_bound_hashed_policy_and_evidence():
    policy = _policy()
    evidence = _evidence()
    decision = evaluate_promotion(_report(policy), policy, evidence)
    assert decision["passed"] is True
    assert decision["farmer_inference_enabled"] is False
    assert decision["artifact_sha256"] == HASH_A
    evidence["checks"]["runtime_parity_valid"] = False
    with pytest.raises(ContractValidationError, match="evidence_sha256:mismatch"):
        evaluate_promotion(_report(policy), policy, evidence)
    other_policy = _policy()
    other_policy["policy_id"] = "different"
    other_policy["policy_sha256"] = _digest(other_policy, "policy_sha256")
    with pytest.raises(ContractValidationError, match="does_not_match_evaluation_lineage"):
        evaluate_promotion(_report(policy), other_policy, _evidence())


def test_farmer_promotion_requires_external_verification_not_json_claims():
    policy = _policy("FARMER")
    report = _report(policy)
    blocked = evaluate_promotion(report, policy, _evidence())
    assert blocked["passed"] is False
    assert "GATE_FAILED:external_release_approval_verified" in blocked["reason_codes"]
    approved = evaluate_promotion(report, policy, _evidence(), approval_verifier=lambda evaluation, supplied_policy, evidence: True)
    assert approved["passed"] is True
    assert approved["farmer_inference_enabled"] is True


def test_registry_binds_candidate_artifact_policy_and_hash_chains_audit(tmp_path):
    policy = _policy()
    decision = evaluate_promotion(_report(policy), policy, _evidence())
    registry = ModelRegistry()
    registry.register_current("banana", _artifact("stable-v1", HASH_B, policy["policy_sha256"]))
    registry.set_candidate("banana", _artifact("candidate-v1", HASH_A, policy["policy_sha256"]))
    registry.promote("banana", decision)
    assert registry.state["crops"]["banana"]["current"]["model_version"] == "candidate-v1"
    assert registry.state["audit"][1]["previous_event_sha256"] == registry.state["audit"][0]["event_sha256"]
    drill = execute_rollback_drill(registry.state, "banana")
    assert drill["passed"] and "does not verify persisted registry reload" in drill["limitations"]
    registry.save_atomic(tmp_path / "registry.json")
    ModelRegistry(json.loads((tmp_path / "registry.json").read_text()))


def test_registry_rejects_candidate_binding_mismatch_and_tampered_audit():
    policy = _policy()
    decision = evaluate_promotion(_report(policy), policy, _evidence())
    registry = ModelRegistry()
    registry.register_current("banana", _artifact("stable-v1", HASH_B, policy["policy_sha256"]))
    registry.set_candidate("banana", _artifact("candidate-v1", HASH_B, policy["policy_sha256"]))
    with pytest.raises(ContractValidationError, match="artifact_sha256_mismatch_candidate"):
        registry.promote("banana", decision)
    state = registry.state
    state["audit"][0]["detail"] = "tampered"
    with pytest.raises(ContractValidationError, match="event_sha256:mismatch"):
        ModelRegistry(state)


def test_policy_and_evidence_validators_reject_schema_drift_and_noninteger_error_budget():
    policy = _policy()
    policy["thresholds"]["max_accepted_errors"] = 0.5
    policy["policy_sha256"] = _digest(policy, "policy_sha256")
    with pytest.raises(ContractValidationError, match="non_negative_integer_required"):
        validate_promotion_policy(policy)
    evidence = _evidence()
    evidence["extra"] = True
    with pytest.raises(ContractValidationError, match="evidence.extra:unknown"):
        validate_promotion_evidence(evidence)
