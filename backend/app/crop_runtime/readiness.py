"""Single fail-closed readiness resolver for crop disease runtimes."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final

from app.banana_v3.artifact_integrity import verify_artifacts
from app.banana_v3.config import ARTIFACT_ROOT as BANANA_ROOT
from app.core.config import settings
from app.legacy_joint.artifacts import (
    verify_bundle_for_controlled_field_test as verify_legacy_bundle,
)
from app.legacy_joint.runtime import ARTIFACT_ROOT as LEGACY_ROOT

from .registry import CropRegistry
from .resolver import RuntimeResolver

RESTRICTED_CROPS = {"redgram", "chilli"}
APP_INTEGRATED = {"banana", "paddy", "cotton", "groundnut", "greengram", *RESTRICTED_CROPS}
# Programmatic invalid-image checks are integrated, but crop-domain/wrong-crop
# validation still requires approved fixtures. Keep eligibility fail-closed.
OOD_SAFETY_INTEGRATED: set[str] = set()
LEGACY_CROPS = {"paddy", "cotton"}
_RESTRICTED_FAILURE_REASONS: Final = {
    "RUNTIME_PACKAGE_MISSING": "file_missing",
    "SHA256_MANIFEST_MISSING": "manifest_missing",
    "SHA256_MANIFEST_INVALID": "manifest_missing",
    "MANIFEST_FILE_MISSING": "file_missing",
    "PACKAGE_HASH_MISMATCH": "hash_mismatch",
    "CHECKPOINT_HASH_MISMATCH": "hash_mismatch",
}


@dataclass(frozen=True)
class CropReadiness:
    crop_id: str
    classification: str
    artifact_present: bool
    integrity_verified: bool
    runtime_loadable: bool
    readiness_reason: str
    api_integrated: bool
    mobile_integrated: bool
    technical_runtime_ready: bool
    internal_testing_eligible: bool
    pilot_testing_eligible: bool
    general_farmer_inference_authorized: bool
    field_validation_complete: bool
    official_accuracy_claim_allowed: bool
    blocking_reasons: list[str]

    def public_dict(self) -> dict[str, object]:
        value = asdict(self)
        value.update(
            {
                "local_runtime_bundle_present": self.artifact_present,
                "local_integrity_verified": self.integrity_verified,
                "local_runtime_ready": self.runtime_loadable,
                "integrity_status": (
                    "VERIFIED"
                    if self.integrity_verified
                    else "LOCAL_RUNTIME_BUNDLE_MISSING"
                    if not self.artifact_present
                    else "FAILED_CLOSED"
                ),
                "technical_testing_eligible": self.internal_testing_eligible,
            }
        )
        return value


class ReadinessResolver:
    def __init__(self, registry: CropRegistry, project_root: Path) -> None:
        self.registry = registry
        self.runtime_resolver = RuntimeResolver(registry, project_root)

    def resolve(self, crop_id: str) -> CropReadiness:
        entry = self.registry.get(crop_id)
        artifact_present, integrity_verified, reason = self._integrity(entry.crop_id)
        runtime_loadable = self._loadable(entry.crop_id, integrity_verified)
        if not entry.crop_enabled:
            reason = "disabled"
            runtime_loadable = False
        elif integrity_verified and not runtime_loadable:
            reason = "load_failed"
        api_integrated = entry.crop_id in APP_INTEGRATED
        mobile_integrated = entry.crop_id in APP_INTEGRATED
        technical = runtime_loadable and api_integrated
        blocking: list[str] = []
        if not artifact_present:
            blocking.append("ARTIFACT_MISSING")
        elif not integrity_verified:
            blocking.append("INTEGRITY_NOT_VERIFIED")
        if not runtime_loadable:
            blocking.append("RUNTIME_NOT_LOADABLE")
        if not api_integrated:
            blocking.append("API_ADAPTER_MISSING")
        if not mobile_integrated:
            blocking.append("MOBILE_ADAPTER_MISSING")
        if entry.crop_id not in OOD_SAFETY_INTEGRATED:
            blocking.append("OOD_SAFETY_NOT_PROVEN")
        if not entry.tamil_nadu_field_validated:
            blocking.append("FIELD_VALIDATION_PENDING")
        blocking.append("GENERAL_FARMER_INFERENCE_NOT_AUTHORIZED")

        internal = (
            technical
            and mobile_integrated
            and (
                entry.crop_id in OOD_SAFETY_INTEGRATED
                or entry.crop_id in RESTRICTED_CROPS
            )
            and entry.crop_enabled
            and (
                entry.disease_detection_enabled
                or entry.crop_id in LEGACY_CROPS
                or entry.crop_id in RESTRICTED_CROPS
            )
        )
        pilot = internal and entry.pilot_inference_eligible
        classification = (
            "INTERNAL_TEST_READY"
            if internal
            else "APP_INTEGRATED_TESTING_BLOCKED"
            if technical and mobile_integrated
            else "BACKEND_RUNTIME_READY"
            if runtime_loadable
            else "BACKEND_REGISTERED_NOT_LOADABLE"
            if entry.crop_enabled
            else "NOT_FOUND"
        )
        return CropReadiness(
            crop_id=entry.crop_id,
            classification=classification,
            artifact_present=artifact_present,
            integrity_verified=integrity_verified,
            runtime_loadable=runtime_loadable,
            readiness_reason=reason,
            api_integrated=api_integrated,
            mobile_integrated=mobile_integrated,
            technical_runtime_ready=technical,
            internal_testing_eligible=internal,
            pilot_testing_eligible=pilot,
            general_farmer_inference_authorized=False,
            field_validation_complete=entry.tamil_nadu_field_validated,
            official_accuracy_claim_allowed=False,
            blocking_reasons=blocking,
        )

    def _integrity(self, crop_id: str) -> tuple[bool, bool, str]:
        try:
            if crop_id == "groundnut":
                if not settings.groundnut_experimental_enabled:
                    return False, False, "feature_disabled"
                try:
                    from app.groundnut_experimental.service import GroundnutPredictionService

                    GroundnutPredictionService().load()
                    return True, True, "ready"
                except Exception:
                    return True, False, "load_failed"
            if crop_id == "greengram":
                if not settings.green_gram_experimental_enabled:
                    return False, False, "feature_disabled"
                try:
                    from app.green_gram_experimental.service import GreenGramPredictionService

                    GreenGramPredictionService().load()
                    return True, True, "ready"
                except Exception:
                    return True, False, "load_failed"
            if crop_id == "banana":
                present = BANANA_ROOT.is_dir()
                if present:
                    verify_artifacts(BANANA_ROOT)
                return present, present, "ready" if present else "file_missing"
            if crop_id in LEGACY_CROPS:
                present = LEGACY_ROOT.is_dir()
                if present:
                    verify_legacy_bundle(LEGACY_ROOT)
                return present, present, "ready" if present else "file_missing"
            if crop_id in RESTRICTED_CROPS:
                from app.restricted_crops.integrity import (
                    RestrictedRuntimeIntegrityError,
                    verify_restricted_package,
                )

                try:
                    verify_restricted_package(crop_id)
                    return True, True, "ready"
                except RestrictedRuntimeIntegrityError as exc:
                    code = str(exc)
                    present = code != "RUNTIME_PACKAGE_MISSING"
                    return present, False, _RESTRICTED_FAILURE_REASONS.get(
                        code, "load_failed"
                    )
            present = self.runtime_resolver.bundle_presence(crop_id)
            if present:
                self.runtime_resolver.verify_integrity(crop_id)
            return present, present, "ready" if present else "file_missing"
        except Exception:
            return True, False, "load_failed"

    @staticmethod
    def _loadable(crop_id: str, integrity_verified: bool) -> bool:
        if not integrity_verified:
            return False
        if crop_id == "banana":
            try:
                from app.banana_v3.inference_service import InferenceService

                InferenceService().load()
                return True
            except Exception:
                return False
        if crop_id in LEGACY_CROPS:
            try:
                from app.legacy_joint.runtime import (
                    get_legacy_joint_controlled_field_test_runtime,
                )

                get_legacy_joint_controlled_field_test_runtime().load()
                return True
            except Exception:
                return False
        if crop_id == "redgram":
            try:
                from app.restricted_crops.runtime import get_restricted_runtime

                get_restricted_runtime(crop_id).load()
                return True
            except Exception:
                return False
        if crop_id == "chilli":
            try:
                from app.restricted_crops.runtime import get_restricted_runtime

                get_restricted_runtime(crop_id).load()
                return True
            except Exception:
                return False
        if crop_id == "greengram":
            return settings.green_gram_experimental_enabled and integrity_verified
        if crop_id == "groundnut":
            return settings.groundnut_experimental_enabled and integrity_verified
        return crop_id in APP_INTEGRATED
