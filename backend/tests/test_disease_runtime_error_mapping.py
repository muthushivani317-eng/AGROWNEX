from app.modules.disease.runtime_errors import classify_runtime_error


class ArtifactIntegrityError(RuntimeError):
    pass


def test_runtime_error_mapping_uses_stable_public_categories() -> None:
    assert classify_runtime_error(RuntimeError("ARTIFACT_MISSING:model.pt")) == (
        "MODEL_ARTIFACT_MISSING"
    )
    assert classify_runtime_error(ArtifactIntegrityError("secret path")) == (
        "MODEL_INTEGRITY_FAILURE"
    )
    assert classify_runtime_error(ModuleNotFoundError("onnxruntime")) == (
        "MODEL_RUNTIME_UNAVAILABLE"
    )
    assert classify_runtime_error(RuntimeError("RUNTIME_PACKAGE_MISSING")) == (
        "MODEL_RUNTIME_UNAVAILABLE"
    )
