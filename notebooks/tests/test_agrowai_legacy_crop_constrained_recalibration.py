import numpy as np
import pytest

from notebooks.agrowai_legacy_crop_constrained_recalibration import (
    CROP_CLASSES,
    class_metrics,
    classify_failure,
    constrain_logits_for_crop,
    evaluate_development,
    validate_crop_support,
    verify_routing_policy,
)


def test_crop_routing_is_a_disjoint_complete_partition() -> None:
    policy = verify_routing_policy()
    groups = policy["groups"]
    all_indices = [
        index for crop in ("paddy", "cotton", "groundnut")
        for index in groups[crop]["global_indices"]
    ]
    assert sorted(all_indices) == list(range(9))
    assert len(all_indices) == len(set(all_indices))
    assert policy["user_crop_confirmation_required"] is True
    assert policy["ai_crop_verification"] is False


@pytest.mark.parametrize(
    ("crop", "expected"),
    [("cotton", [0, 1, 2]), ("groundnut", [3, 4]), ("paddy", [5, 6, 7, 8])],
)
def test_raw_logits_are_restricted_before_softmax(crop: str, expected: list[int]) -> None:
    logits = np.arange(18, dtype=np.float64).reshape(2, 9)
    constrained = constrain_logits_for_crop(logits, crop)
    assert constrained.tolist() == logits[:, expected].tolist()


def test_each_crop_can_return_only_its_own_classes() -> None:
    logits = np.zeros((1, 9), dtype=np.float64)
    for crop, classes in CROP_CLASSES.items():
        constrained = constrain_logits_for_crop(logits, crop)
        assert constrained.shape[1] == len(classes)


def test_unknown_crop_fails_closed() -> None:
    with pytest.raises(ValueError, match="UNKNOWN_CROP"):
        constrain_logits_for_crop(np.zeros((1, 9)), "banana")


def test_insufficient_per_class_calibration_fails_closed() -> None:
    labels = np.array([5, 5, 6, 6, 7, 7, 8])
    with pytest.raises(RuntimeError, match="INSUFFICIENT_CROP_CALIBRATION_DATA"):
        validate_crop_support(labels, "paddy")


def test_sufficient_crop_calibration_records_counts() -> None:
    labels = np.array([3, 3, 4, 4])
    result = validate_crop_support(labels, "groundnut")
    assert result["sample_count"] == 4
    assert result["per_class_counts"] == {
        "groundnut_healthy": 2,
        "groundnut_rust": 2,
    }


def test_development_metrics_apply_calibration_and_abstention() -> None:
    logits = np.array([[5.0, 0.0], [0.0, 5.0], [2.0, 1.0], [1.0, 2.0]])
    labels = np.array([0, 1, 0, 1])
    result = evaluate_development(
        logits, labels, 1.2, 0.6, 0.0, ["healthy", "disease"]
    )
    assert result["label"] == "DEVELOPMENT_ONLY_NOT_AN_OFFICIAL_ACCURACY_CLAIM"
    assert result["sample_count"] == 4
    assert result["accepted_count"] + result["abstention_count"] == 4
    assert len(result["per_class"]) == 2


def test_macro_f1_and_per_class_recall_are_reported() -> None:
    macro, rows = class_metrics(
        np.array([0, 1, 1, 1]), np.array([0, 0, 1, 1]), ["a", "b"]
    )
    assert 0 <= macro <= 1
    assert rows[0]["recall"] == 0.5
    assert rows[1]["recall"] == 1.0


@pytest.mark.parametrize(
    ("message", "decision"),
    [
        ("INSUFFICIENT_CROP_CALIBRATION_DATA:paddy", "INSUFFICIENT_CROP_CALIBRATION_DATA"),
        ("ONNX_ACTUAL_OPSET_NOT_17:18", "ONNX_EXPORT_FAILED"),
        ("PARITY_FAILED", "PARITY_FAILED"),
        ("CALIBRATION_NLL_SAFETY_FAILURE", "RECALIBRATION_FAILED"),
    ],
)
def test_failure_classification(message: str, decision: str) -> None:
    assert classify_failure(RuntimeError(message)) == decision
