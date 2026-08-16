"""Unified, group-aware offline evaluation for crop and disease classifiers."""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import defaultdict
from typing import Any, Callable

from .contracts import ContractValidationError, SCHEMA_VERSION, SHA256_RE

EPSILON = 1e-15
RECORD_FIELDS = {
    "sample_id",
    "true_label",
    "probabilities",
    "accepted",
    "is_ood",
    "latency_ms",
    "evaluation_group_id",
    "slices",
}
REPORT_FIELDS = {
    "schema_version",
    "lineage",
    "labels",
    "metrics",
    "slices",
    "bootstrap",
    "report_sha256",
}
METRIC_FIELDS = {
    "sample_count", "accuracy", "balanced_accuracy", "micro_f1", "macro_f1", "per_class",
    "confusion_matrix", "calibration", "selection", "ood", "latency_ms", "confidence_intervals",
}


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def _report_fingerprint(report: dict[str, Any]) -> str:
    payload = {key: value for key, value in report.items() if key != "report_sha256"}
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _validate_lineage(lineage: Any) -> list[str]:
    if not isinstance(lineage, dict):
        return ["lineage:object_required"]
    errors: list[str] = []
    allowed = {"model_version", "artifact_sha256", "policy_sha256", "dataset_sha256", "code_sha"}
    errors.extend(f"lineage.{key}:unknown" for key in sorted(set(lineage) - allowed))
    for key in allowed:
        if key not in lineage:
            errors.append(f"lineage.{key}:missing")
    for key in ("model_version", "code_sha"):
        if key in lineage and not _nonempty(lineage[key]):
            errors.append(f"lineage.{key}:nonempty_string_required")
    for key in ("artifact_sha256", "policy_sha256", "dataset_sha256"):
        if key in lineage and (not isinstance(lineage[key], str) or not SHA256_RE.fullmatch(lineage[key])):
            errors.append(f"lineage.{key}:invalid")
    return errors


def _validate_records(records: list[dict[str, Any]], labels: list[str]) -> None:
    errors: list[str] = []
    if not isinstance(records, list) or not records:
        errors.append("records:non_empty_required")
    if not isinstance(labels, list) or len(labels) < 2 or len(set(labels)) != len(labels) or any(not _nonempty(label) for label in labels):
        errors.append("labels:at_least_two_nonempty_unique_required")
    if errors:
        raise ContractValidationError(errors)
    label_set = set(labels)
    sample_ids: set[str] = set()
    id_count = 0
    for index, record in enumerate(records):
        prefix = f"records[{index}]"
        if not isinstance(record, dict):
            errors.append(f"{prefix}:object_required")
            continue
        errors.extend(f"{prefix}.{field}:unknown" for field in sorted(set(record) - RECORD_FIELDS))
        for field in ("sample_id", "true_label", "probabilities", "accepted", "is_ood", "latency_ms", "evaluation_group_id"):
            if field not in record:
                errors.append(f"{prefix}.{field}:missing")
        if any(field not in record for field in ("sample_id", "true_label", "probabilities", "accepted", "is_ood", "latency_ms", "evaluation_group_id")):
            continue
        if not _nonempty(record["sample_id"]):
            errors.append(f"{prefix}.sample_id:nonempty_string_required")
        elif record["sample_id"] in sample_ids:
            errors.append(f"{prefix}.sample_id:duplicate:{record['sample_id']}")
        else:
            sample_ids.add(record["sample_id"])
        if not _nonempty(record["evaluation_group_id"]):
            errors.append(f"{prefix}.evaluation_group_id:nonempty_string_required")
        if not isinstance(record["is_ood"], bool):
            errors.append(f"{prefix}.is_ood:boolean_required")
        elif record["is_ood"]:
            if record["true_label"] is not None:
                errors.append(f"{prefix}.true_label:must_be_null_for_ood")
        else:
            id_count += 1
            if record["true_label"] not in label_set:
                errors.append(f"{prefix}.true_label:unknown")
        probabilities = record["probabilities"]
        if not isinstance(probabilities, dict) or set(probabilities) != label_set:
            errors.append(f"{prefix}.probabilities:label_set_mismatch")
        else:
            values = list(probabilities.values())
            if any(not _number(value) or value < 0 for value in values):
                errors.append(f"{prefix}.probabilities:invalid")
            elif not math.isclose(sum(values), 1.0, rel_tol=1e-6, abs_tol=1e-6):
                errors.append(f"{prefix}.probabilities:must_sum_to_one")
        if not isinstance(record["accepted"], bool):
            errors.append(f"{prefix}.accepted:boolean_required")
        if not _number(record["latency_ms"]) or record["latency_ms"] < 0:
            errors.append(f"{prefix}.latency_ms:invalid")
        if "slices" in record:
            slices = record["slices"]
            if not isinstance(slices, dict) or any(not _nonempty(key) or not _nonempty(value) for key, value in slices.items()):
                errors.append(f"{prefix}.slices:nonempty_string_map_required")
    if id_count == 0:
        errors.append("records:in_distribution_sample_required")
    if errors:
        raise ContractValidationError(errors)


def _id_core(records: list[dict[str, Any]], labels: list[str]) -> dict[str, Any]:
    """Metrics for in-distribution samples only; OOD never enters these values."""
    index = {label: position for position, label in enumerate(labels)}
    matrix = [[0 for _ in labels] for _ in labels]
    confidences: list[float] = []
    correctness: list[bool] = []
    nll = 0.0
    brier = 0.0
    for record in records:
        probabilities = record["probabilities"]
        predicted = max(labels, key=lambda label: probabilities[label])
        confidence = float(probabilities[predicted])
        correct = predicted == record["true_label"]
        confidences.append(confidence)
        correctness.append(correct)
        matrix[index[record["true_label"]]][index[predicted]] += 1
        nll -= math.log(max(float(probabilities[record["true_label"]]), EPSILON))
        brier += sum((float(probabilities[label]) - float(label == record["true_label"])) ** 2 for label in labels)

    per_class: dict[str, dict[str, float | int]] = {}
    recalls: list[float] = []
    f1s: list[float] = []
    for position, label in enumerate(labels):
        tp = matrix[position][position]
        support = sum(matrix[position])
        predicted_count = sum(row[position] for row in matrix)
        precision = tp / predicted_count if predicted_count else 0.0
        recall = tp / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1, "support": support}
        recalls.append(recall)
        f1s.append(f1)

    accepted = [index for index, record in enumerate(records) if record["accepted"]]
    accepted_correct = sum(correctness[index] for index in accepted)
    bins: list[dict[str, float | int | None]] = []
    ece = 0.0
    for bin_index in range(15):
        low, high = bin_index / 15, (bin_index + 1) / 15
        members = [index for index, confidence in enumerate(confidences) if low <= confidence <= high and (bin_index == 14 or confidence < high)]
        bin_conf = _mean([confidences[index] for index in members])
        bin_accuracy = _mean([float(correctness[index]) for index in members])
        if members and bin_conf is not None and bin_accuracy is not None:
            ece += len(members) / len(records) * abs(bin_accuracy - bin_conf)
        bins.append({"lower": low, "upper": high, "count": len(members), "accuracy": bin_accuracy, "confidence": bin_conf})
    risk_coverage = []
    for threshold in (0.0, 0.5, 0.75, 0.9, 0.95, 0.99):
        selected = [index for index, confidence in enumerate(confidences) if confidence >= threshold]
        selected_accuracy = _mean([float(correctness[index]) for index in selected])
        risk_coverage.append({"confidence_threshold": threshold, "coverage": len(selected) / len(records), "accuracy": selected_accuracy, "risk": None if selected_accuracy is None else 1 - selected_accuracy})
    latency = [float(record["latency_ms"]) for record in records]
    accuracy = sum(correctness) / len(records)
    return {
        "sample_count": len(records), "accuracy": accuracy, "balanced_accuracy": sum(recalls) / len(recalls),
        "micro_f1": accuracy, "macro_f1": sum(f1s) / len(f1s), "per_class": per_class,
        "confusion_matrix": {"labels": labels, "values": matrix},
        "calibration": {"nll": nll / len(records), "brier": brier / len(records), "ece_15": ece, "bins": bins},
        "selection": {"accepted_count": len(accepted), "abstained_count": len(records) - len(accepted), "coverage": len(accepted) / len(records), "accepted_accuracy": accepted_correct / len(accepted) if accepted else None, "accepted_errors": len(accepted) - accepted_correct, "risk_coverage_curve": risk_coverage},
        "latency_ms": {"mean": _mean(latency), "p50": _percentile(latency, 0.50), "p95": _percentile(latency, 0.95), "p99": _percentile(latency, 0.99)},
    }


def _ood_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "sample_count": len(records),
        "false_accept_count": sum(record["accepted"] for record in records),
        "false_accept_rate": sum(record["accepted"] for record in records) / len(records) if records else None,
    }


def _group_bootstrap_ci(
    records: list[dict[str, Any]], labels: list[str], metric: Callable[[dict[str, Any]], float | None], iterations: int, seed: int
) -> dict[str, float | int] | None:
    if iterations <= 0:
        return None
    by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_group[record["evaluation_group_id"]].append(record)
    groups = sorted(by_group)
    rng = random.Random(seed)
    estimates: list[float] = []
    undefined = 0
    for _ in range(iterations):
        sample: list[dict[str, Any]] = []
        for _ in groups:
            sample.extend(by_group[rng.choice(groups)])
        value = metric(_id_core(sample, labels))
        if value is None or not math.isfinite(value):
            undefined += 1
        else:
            estimates.append(value)
    if not estimates:
        return None
    return {"lower_95": float(_percentile(estimates, 0.025)), "upper_95": float(_percentile(estimates, 0.975)), "defined_iterations": len(estimates), "undefined_iterations": undefined}


def validate_evaluation_report(report: dict[str, Any]) -> dict[str, Any]:
    """Validate closed report shape and its canonical integrity hash before use."""
    if not isinstance(report, dict):
        raise ContractValidationError(["evaluation:object_required"])
    errors: list[str] = []
    errors.extend(f"evaluation.{key}:unknown" for key in sorted(set(report) - REPORT_FIELDS))
    for key in REPORT_FIELDS:
        if key not in report:
            errors.append(f"evaluation.{key}:missing")
    if errors:
        raise ContractValidationError(errors)
    if report["schema_version"] != SCHEMA_VERSION:
        errors.append("evaluation.schema_version:unsupported")
    errors.extend(_validate_lineage(report["lineage"]))
    labels = report["labels"]
    if not isinstance(labels, list) or len(labels) < 2 or len(set(labels)) != len(labels) or any(not _nonempty(label) for label in labels):
        errors.append("evaluation.labels:at_least_two_nonempty_unique_required")
    metrics = report["metrics"]
    if not isinstance(metrics, dict):
        errors.append("evaluation.metrics:object_required")
    else:
        errors.extend(f"evaluation.metrics.{key}:unknown" for key in sorted(set(metrics) - METRIC_FIELDS))
        for key in METRIC_FIELDS:
            if key not in metrics:
                errors.append(f"evaluation.metrics.{key}:missing")
        for key in ("accuracy", "balanced_accuracy", "micro_f1", "macro_f1"):
            value = metrics.get(key)
            if not _number(value) or not 0 <= value <= 1:
                errors.append(f"evaluation.metrics.{key}:invalid")
        if not isinstance(metrics.get("sample_count"), int) or isinstance(metrics.get("sample_count"), bool) or metrics.get("sample_count", 0) < 1:
            errors.append("evaluation.metrics.sample_count:positive_integer_required")
        for key in ("selection", "calibration", "ood", "latency_ms", "per_class"):
            if not isinstance(metrics.get(key), dict):
                errors.append(f"evaluation.metrics.{key}:object_required")
    if not isinstance(report["slices"], dict):
        errors.append("evaluation.slices:object_required")
    bootstrap = report["bootstrap"]
    if not isinstance(bootstrap, dict) or set(bootstrap) != {"iterations", "seed", "method", "group_field"}:
        errors.append("evaluation.bootstrap:closed_contract_required")
    elif bootstrap["method"] != "cluster_bootstrap" or bootstrap["group_field"] != "evaluation_group_id" or not isinstance(bootstrap["iterations"], int) or isinstance(bootstrap["iterations"], bool) or bootstrap["iterations"] < 0 or not isinstance(bootstrap["seed"], int) or isinstance(bootstrap["seed"], bool):
        errors.append("evaluation.bootstrap:invalid")
    digest = report["report_sha256"]
    if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
        errors.append("evaluation.report_sha256:invalid")
    elif digest != _report_fingerprint(report):
        errors.append("evaluation.report_sha256:mismatch")
    if errors:
        raise ContractValidationError(errors)
    return dict(report)


def build_evaluation_report(
    records: list[dict[str, Any]], labels: list[str], lineage: dict[str, Any], *, bootstrap_iterations: int = 200, seed: int = 41212
) -> dict[str, Any]:
    """Return a deterministic report with ID metrics and OOD safety metrics separated."""
    _validate_records(records, labels)
    lineage_errors = _validate_lineage(lineage)
    if lineage_errors:
        raise ContractValidationError(lineage_errors)
    if not isinstance(bootstrap_iterations, int) or isinstance(bootstrap_iterations, bool) or bootstrap_iterations < 0:
        raise ContractValidationError(["bootstrap_iterations:non_negative_integer_required"])
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ContractValidationError(["seed:integer_required"])
    id_records = [record for record in records if record["is_ood"] is False]
    ood_records = [record for record in records if record["is_ood"] is True]
    metrics = _id_core(id_records, labels)
    metrics["ood"] = _ood_metrics(ood_records)
    metrics["confidence_intervals"] = {
        "accuracy": _group_bootstrap_ci(id_records, labels, lambda value: value["accuracy"], bootstrap_iterations, seed),
        "macro_f1": _group_bootstrap_ci(id_records, labels, lambda value: value["macro_f1"], bootstrap_iterations, seed + 1),
        "coverage": _group_bootstrap_ci(id_records, labels, lambda value: value["selection"]["coverage"], bootstrap_iterations, seed + 2),
        "accepted_accuracy": _group_bootstrap_ci(id_records, labels, lambda value: value["selection"]["accepted_accuracy"], bootstrap_iterations, seed + 3),
    }
    slices: dict[str, dict[str, Any]] = {}
    slice_values: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        for name, value in record.get("slices", {}).items():
            slice_values[(str(name), str(value))].append(record)
    for (name, value), members in sorted(slice_values.items()):
        slice_id = [record for record in members if record["is_ood"] is False]
        slice_ood = [record for record in members if record["is_ood"] is True]
        slices.setdefault(name, {})[value] = {"id_metrics": _id_core(slice_id, labels) if slice_id else None, "ood": _ood_metrics(slice_ood)}
    report = {
        "schema_version": SCHEMA_VERSION, "lineage": dict(lineage), "labels": list(labels), "metrics": metrics,
        "slices": slices, "bootstrap": {"iterations": bootstrap_iterations, "seed": seed, "method": "cluster_bootstrap", "group_field": "evaluation_group_id"},
    }
    report["report_sha256"] = _report_fingerprint(report)
    validate_evaluation_report(report)
    return report
