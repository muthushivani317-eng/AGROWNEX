import numpy as np
import pytest

from notebooks.agrowai_legacy_joint_runtime_reconstruction import (
    EXPECTED_CLASSES,
    crop_constrained,
    extract_preprocessing_definition,
    fit_temperature,
    FROZEN_PREPROCESSING_EVIDENCE,
    ordered_mapping,
    preprocessing,
    probabilities,
    select_policy,
    square_image_size,
    threshold_rows,
    verify_checkpoint_identity,
)


def test_mapping_object_is_sorted_by_numeric_index() -> None:
    reverse_items = list(reversed(list(enumerate(EXPECTED_CLASSES))))
    value = {class_id: index for index, class_id in reverse_items}
    assert ordered_mapping(value) == EXPECTED_CLASSES


def test_mapping_rejects_non_contiguous_indices() -> None:
    with pytest.raises(ValueError, match="CLASS_INDICES_NOT_CONTIGUOUS"):
        ordered_mapping({"a": 0, "b": 2})


def test_mapping_accepts_integer_dictionary_keys_as_class_names() -> None:
    assert ordered_mapping({101: 0, 202: 1}) == [101, 202]


def test_temperature_fit_never_worsens_nll_and_is_reproducible() -> None:
    logits = np.array([
        [8.0, 0.0], [8.0, 0.0], [0.0, 8.0], [0.0, 8.0],
        [8.0, 0.0], [0.0, 8.0],
    ])
    labels = np.array([0, 1, 1, 1, 0, 0])
    first = fit_temperature(logits, labels)
    second = fit_temperature(logits, labels)
    assert first["nll_after"] <= first["nll_before"] + 1e-10
    assert first["temperature"] == pytest.approx(second["temperature"], rel=1e-10)
    assert first["temperature"] > 1


def test_scaled_probabilities_sum_to_one() -> None:
    logits = np.array([[1.2, -0.5, 0.3], [0.2, 0.4, -1.0]])
    assert np.allclose(probabilities(logits, 1.3).sum(axis=1), 1)


def test_crop_constraint_removes_other_crop_outputs() -> None:
    logits = np.zeros((3, 9))
    labels = np.array([0, 3, 5])
    local, local_labels, source_rows = crop_constrained(logits, labels, "paddy")
    assert local.shape == (1, 4)
    assert local_labels.tolist() == [0]
    assert source_rows.tolist() == [2]


def test_threshold_selection_uses_explicit_gate() -> None:
    probs = np.array([[0.95, 0.05], [0.05, 0.95], [0.94, 0.06], [0.04, 0.96]])
    labels = np.array([0, 1, 0, 1])
    rows = threshold_rows(probs, labels, "crop_constrained", "synthetic")
    selected = select_policy(rows)
    assert selected is not None
    assert selected.passes_gate
    assert selected.coverage == 1.0


def test_square_image_size_accepts_scalar_or_square_shape() -> None:
    assert square_image_size(224) == 224
    assert square_image_size([3, 224, 224]) == 224
    with pytest.raises(RuntimeError):
        square_image_size([224, 256])


def test_checkpoint_identity_requires_epoch_architecture_mapping_and_nine_outputs() -> None:
    state = {"classifier.3.weight": np.zeros((9, 1280)), "classifier.3.bias": np.zeros(9)}
    checkpoint = {
        "epoch": 6,
        "architecture": "mobilenet_v3_small",
        "class_to_index": {name: index for index, name in enumerate(EXPECTED_CLASSES)},
    }
    result = verify_checkpoint_identity(state, checkpoint)
    assert result["epoch"] == 6
    assert result["ordered_mapping"] == EXPECTED_CLASSES


def test_extracts_exact_frozen_inference_preprocessing() -> None:
    result = extract_preprocessing_definition(FROZEN_PREPROCESSING_EVIDENCE)
    assert result["decision"] == "PREPROCESSING_PROVEN"
    assert result["image_size"] == 224
    assert result["inference"]["resize"]["size"] == [224, 224]
    assert result["inference"]["resize"]["crop"] is None
    assert result["mean"] == [0.485, 0.456, 0.406]
    assert result["std"] == [0.229, 0.224, 0.225]
    assert result["training_augmentation"]["runtime_inference"] is False


def test_preprocessing_walk_handles_integer_dictionary_keys() -> None:
    snapshot = {0: {"image_size": 224}}
    result = preprocessing(snapshot, {1: {"architecture": "mobilenet_v3_small"}})
    assert result["decision"] == "PREPROCESSING_PROVEN"


def test_preprocessing_fails_closed_on_conflicting_image_size() -> None:
    with pytest.raises(RuntimeError, match="PREPROCESSING_AMBIGUOUS"):
        preprocessing({"image_size": 256}, {"image_size": 224})


def test_unproven_preprocessing_decision_is_rejected() -> None:
    evidence = dict(FROZEN_PREPROCESSING_EVIDENCE)
    evidence["decision"] = "PREPROCESSING_NOT_FOUND"
    with pytest.raises(RuntimeError, match="EXACT_PREPROCESSING_NOT_PROVEN"):
        extract_preprocessing_definition(evidence)
