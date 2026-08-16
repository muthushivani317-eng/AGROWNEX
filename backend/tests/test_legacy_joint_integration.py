import io
import json
import uuid
from pathlib import Path

import httpx
import numpy as np
import pytest
from app.api.errors import register_exception_handlers
from app.core.database import get_session
from app.legacy_joint import api_router as legacy_api
from app.legacy_joint import artifacts as legacy_artifacts
from app.legacy_joint.artifacts import EXPECTED_CLASSES, verify_bundle
from app.legacy_joint.field_test_override import (
    TEST_MODE_MARKER,
    LegacyJointFieldTestGate,
    LegacyJointOverrideAuditLogger,
)
from app.legacy_joint.runtime import ARTIFACT_ROOT, LegacyJointRuntime
from app.modules.auth.constants import RoleName, UserStatus
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.rbac_models import Role, UserRole
from fastapi import FastAPI
from PIL import Image
from sqlalchemy import select


def _png_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (224, 224), (25, 110, 35)).save(output, "PNG")
    return output.getvalue()


async def _user_with_role(db_session, role_name: str) -> User:
    user = User(firebase_uid=f"legacy-{uuid.uuid4()}", status=UserStatus.ACTIVE)
    db_session.add(user)
    await db_session.flush()
    role = (
        await db_session.execute(select(Role).where(Role.role_name == role_name))
    ).scalar_one()
    db_session.add(UserRole(user_id=user.id, role_id=role.id))
    await db_session.flush()
    return user


def _app_for(db_session, user: User) -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(legacy_api.router)

    async def session_override():
        yield db_session

    async def user_override():
        return user

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_current_user] = user_override
    return app


def test_imported_bundle_hashes_opset_parity_mapping_and_authorized_decision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_json = legacy_artifacts._json

    def authorized_decision(path: Path) -> dict:
        value = original_json(path)
        if path.name == "crop_constrained_recalibration_decision.json":
            return {**value, "app_enablement_allowed": True}
        return value

    monkeypatch.setattr(legacy_artifacts, "_json", authorized_decision)
    result = verify_bundle(ARTIFACT_ROOT)
    assert result["decision"] == "READY_FOR_BACKEND_INTEGRATION"
    assert result["actual_opset"] == 17
    assert result["parity_passed"] is True
    assert result["classes"] == EXPECTED_CLASSES


def test_current_bundle_fails_closed_when_app_enablement_is_not_authorized() -> None:
    with pytest.raises(
        legacy_artifacts.LegacyJointArtifactError,
        match="^APP_ENABLEMENT_NOT_AUTHORIZED$",
    ):
        verify_bundle(ARTIFACT_ROOT)


def test_controlled_field_test_verifier_does_not_read_release_decision_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_json = legacy_artifacts._json
    decision_read = False

    def reject_decision_read(path: Path) -> dict:
        nonlocal decision_read
        if path.name == "crop_constrained_recalibration_decision.json":
            decision_read = True
            raise AssertionError("field-test verifier must not parse release decision")
        return original_json(path)

    monkeypatch.setattr(legacy_artifacts, "_json", reject_decision_read)
    result = legacy_artifacts.verify_bundle_for_controlled_field_test(ARTIFACT_ROOT)
    assert result["decision"] is None
    assert result["release_decision_consulted"] is False
    assert decision_read is False


def test_field_test_gate_defaults_off_and_new_process_state_is_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.legacy_joint.field_test_override.settings.legacy_joint_field_test_override_permitted",
        True,
    )
    first_process = LegacyJointFieldTestGate()
    with pytest.raises(RuntimeError, match="OVERRIDE_OFF"):
        first_process.require_active()
    first_process.activate("kvk-2026-08-08")
    assert first_process.require_active() == "kvk-2026-08-08"
    assert LegacyJointFieldTestGate().status()["active"] is False
    assert first_process.deactivate() == "kvk-2026-08-08"
    with pytest.raises(RuntimeError, match="OVERRIDE_OFF"):
        first_process.require_active()


def test_field_test_gate_cannot_activate_without_explicit_server_permission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.legacy_joint.field_test_override.settings.legacy_joint_field_test_override_permitted",
        False,
    )
    with pytest.raises(RuntimeError, match="OVERRIDE_NOT_PERMITTED"):
        LegacyJointFieldTestGate().activate("kvk-2026-08-08")


@pytest.mark.asyncio
@pytest.mark.parametrize("crop", ["paddy", "cotton", "groundnut"])
async def test_override_off_refuses_all_legacy_crops_before_runtime(
    db_session, monkeypatch: pytest.MonkeyPatch, crop: str
) -> None:
    user = await _user_with_role(db_session, RoleName.KVK_REVIEWER.value)
    monkeypatch.setattr(
        "app.legacy_joint.field_test_override.settings.legacy_joint_field_test_override_permitted",
        False,
    )
    legacy_api.legacy_joint_field_test_gate.deactivate()
    runtime_called = False

    def forbidden_predict(*_args, **_kwargs):
        nonlocal runtime_called
        runtime_called = True
        raise AssertionError("runtime must not run while override is off")

    monkeypatch.setattr(legacy_api.field_test_runtime, "predict", forbidden_predict)
    transport = httpx.ASGITransport(app=_app_for(db_session, user))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/disease/{crop}/predict",
            files={"image": ("leaf.png", _png_bytes(), "image/png")},
            data={
                "crop_confirmed": "true",
                "crop_confirmation_token": "not-consumed-while-off",
            },
        )
    assert response.status_code == 503
    assert response.json()["error_code"] == "LEGACY_JOINT_FIELD_TEST_OVERRIDE_OFF"
    assert runtime_called is False


@pytest.mark.asyncio
async def test_override_on_controlled_tester_gets_real_runtime_result_and_marker(
    db_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = await _user_with_role(db_session, RoleName.KVK_REVIEWER.value)
    monkeypatch.setattr(
        "app.legacy_joint.field_test_override.settings.legacy_joint_field_test_override_permitted",
        True,
    )

    async def decoded_image(*_args, **_kwargs):
        return Image.new("RGB", (224, 224), (25, 110, 35)), _png_bytes(), "image/png"

    monkeypatch.setattr(legacy_api, "_image", decoded_image)
    monkeypatch.setattr(legacy_api.field_test_logger, "record", lambda **_kwargs: None)
    monkeypatch.setattr(
        legacy_api.legacy_joint_override_audit_logger,
        "record",
        lambda **_kwargs: None,
    )
    legacy_api.legacy_joint_field_test_gate.activate("kvk-2026-08-08")
    try:
        transport = httpx.ASGITransport(app=_app_for(db_session, user))
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.post(
                "/disease/paddy/predict",
                files={"image": ("leaf.png", _png_bytes(), "image/png")},
                data={
                    "crop_confirmed": "true",
                    "crop_confirmation_token": "decoded-image-test-bypass",
                },
            )
    finally:
        legacy_api.legacy_joint_field_test_gate.deactivate()
    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] in {"accepted", "uncertain"}
    assert 0 <= body["calibrated_confidence"] <= 1
    assert body["test_mode"] == {
        "active": True,
        "code": "LEGACY_JOINT_CONTROLLED_FIELD_TEST_OVERRIDE",
        "display_required": True,
        "banner_text": TEST_MODE_MARKER,
        "session_id": "kvk-2026-08-08",
    }


@pytest.mark.asyncio
async def test_override_on_still_refuses_ordinary_farmer_before_runtime(
    db_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = await _user_with_role(db_session, RoleName.FARMER.value)
    monkeypatch.setattr(
        "app.legacy_joint.field_test_override.settings.legacy_joint_field_test_override_permitted",
        True,
    )
    legacy_api.legacy_joint_field_test_gate.activate("kvk-2026-08-08")
    runtime_called = False

    def forbidden_predict(*_args, **_kwargs):
        nonlocal runtime_called
        runtime_called = True
        raise AssertionError("ordinary farmer must not reach runtime")

    monkeypatch.setattr(legacy_api.field_test_runtime, "predict", forbidden_predict)
    try:
        transport = httpx.ASGITransport(app=_app_for(db_session, user))
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.post(
                "/disease/paddy/predict",
                files={"image": ("leaf.png", _png_bytes(), "image/png")},
                data={
                    "crop_confirmed": "true",
                    "crop_confirmation_token": "must-not-be-consumed",
                },
            )
    finally:
        legacy_api.legacy_joint_field_test_gate.deactivate()
    assert response.status_code == 403
    assert response.json()["error_code"] == "TESTER_ROLE_REQUIRED"
    assert runtime_called is False


def test_legacy_override_audit_is_separate_structured_and_privacy_minimized(
    tmp_path: Path,
) -> None:
    from types import SimpleNamespace

    path = tmp_path / "legacy-override.jsonl"
    logger = LegacyJointOverrideAuditLogger(path)
    tester = SimpleNamespace(
        user=SimpleNamespace(id="private-user-id"), role="kvk_reviewer"
    )
    logger.record(
        event="PREDICTION_SERVED",
        session_id="kvk-2026-08-08",
        tester=tester,
        crop="paddy",
        predicted_class="rice_blast",
        confidence=0.91,
        outcome="accepted",
    )
    row = json.loads(path.read_text("utf-8"))
    assert row["record_type"] == "LEGACY_JOINT_CONTROLLED_FIELD_TEST_OVERRIDE_AUDIT"
    assert row["session_id"] == "kvk-2026-08-08"
    assert row["test_mode_marker"] == TEST_MODE_MARKER
    assert row["tester_subject_hash"] != "private-user-id"
    assert "private-user-id" not in path.read_text("utf-8")


def test_current_bundle_blocks_runtime_and_crop_identity_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = LegacyJointRuntime(ARTIFACT_ROOT)
    with pytest.raises(
        legacy_artifacts.LegacyJointArtifactError,
        match="^APP_ENABLEMENT_NOT_AUTHORIZED$",
    ):
        runtime.predict(
            "rice", Image.new("RGB", (32, 32), "green"), crop_confirmed=True
        )

    # Crop identity no longer dispatches disease inference. The runtime-level
    # app-enablement refusal above is the remaining general-release boundary.


def test_crop_specific_temperatures_and_thresholds_are_distinct_and_verified() -> None:
    expected = {
        "paddy": (1.185621730465097, 0.75, 0.0),
        "cotton": (0.11945409775578275, 0.5, 0.0),
        "groundnut": (0.5215946352798655, 0.5, 0.0),
    }
    for crop, values in expected.items():
        temperature = json.loads(
            (ARTIFACT_ROOT / f"calibration/{crop}_temperature.json").read_text("utf-8")
        )
        policy = json.loads(
            (ARTIFACT_ROOT / f"thresholds/{crop}_abstention_policy.json").read_text(
                "utf-8"
            )
        )
        assert temperature["temperature"] == values[0]
        assert policy["confidence_threshold"] == values[1]
        assert policy["margin_threshold"] == values[2]
        assert policy["passes_gate"] is True


class _Input:
    name = "image"


class _FakeSession:
    def __init__(self, logits: list[float]) -> None:
        self.logits = np.asarray([logits], dtype=np.float32)

    def get_inputs(self):
        return [_Input()]

    def run(self, *_args, **_kwargs):
        return [self.logits]


def _runtime(logits: list[float]) -> LegacyJointRuntime:
    runtime = LegacyJointRuntime(Path("unused"))
    runtime._verified = {"actual_opset": 17, "parity_passed": True}
    runtime._session = _FakeSession(logits)
    runtime._routing = {
        "cotton": {
            "global_indices": [0, 1, 2],
            "class_ids": EXPECTED_CLASSES[0:3],
            "forbidden_class_ids": EXPECTED_CLASSES[3:],
        },
        "groundnut": {
            "global_indices": [3, 4],
            "class_ids": EXPECTED_CLASSES[3:5],
            "forbidden_class_ids": EXPECTED_CLASSES[0:3] + EXPECTED_CLASSES[5:],
        },
        "paddy": {
            "global_indices": [5, 6, 7, 8],
            "class_ids": EXPECTED_CLASSES[5:],
            "forbidden_class_ids": EXPECTED_CLASSES[:5],
        },
    }
    runtime._temperature = {"rice": 1.0, "cotton": 1.0, "groundnut": 1.0}
    runtime._thresholds = {
        "rice": (0.5, 0.0),
        "cotton": (0.5, 0.0),
        "groundnut": (0.5, 0.0),
    }
    return runtime


def test_crop_restriction_happens_before_softmax_and_blocks_cross_crop_top_logit() -> None:
    runtime = _runtime([100.0, 0.0, 0.0, 0.0, 1.0, 0.0, 4.0, 0.0, 0.0])
    result = runtime.predict(
        "rice", Image.new("RGB", (32, 32), "green"), crop_confirmed=True
    )
    assert result.class_id == "rice_blast"
    assert result.class_id not in EXPECTED_CLASSES[:5]


def test_each_crop_can_only_return_its_own_classes() -> None:
    logits = [9.0, 1.0, 0.0, 8.0, 0.0, 7.0, 0.0, 0.0, 0.0]
    runtime = _runtime(logits)
    for crop, allowed in {
        "cotton": EXPECTED_CLASSES[:3],
        "groundnut": EXPECTED_CLASSES[3:5],
        "rice": EXPECTED_CLASSES[5:],
    }.items():
        result = runtime.predict(
            crop, Image.new("RGB", (32, 32), "green"), crop_confirmed=True
        )
        assert result.class_id in allowed


def test_uncertain_result_hides_candidate_class() -> None:
    runtime = _runtime([0.0] * 9)
    runtime._thresholds["rice"] = (0.9, 0.0)
    result = runtime.predict(
        "rice", Image.new("RGB", (32, 32), "green"), crop_confirmed=True
    )
    assert result.outcome == "uncertain"
    assert result.class_id is None


def test_user_crop_confirmation_is_mandatory() -> None:
    runtime = _runtime([0.0] * 9)
    try:
        runtime.predict("rice", Image.new("RGB", (32, 32)), crop_confirmed=False)
    except ValueError as exc:
        assert str(exc) == "USER_CROP_CONFIRMATION_REQUIRED"
    else:
        raise AssertionError("crop confirmation gate did not fail closed")
