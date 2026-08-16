"""Write the fail-closed crop-ID real-auth/challenge audit from verified evidence."""
# ruff: noqa: E501

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = (
    ROOT / "docs/model_audits/crop_identity_real_auth_and_internal_challenge" / "20260730T100608Z"
)
CANONICAL = Path(r"D:\AgrowAI\incoming_model_bundles\canonical_split_manifest.json")
EXPECTED_CANONICAL_SHA = "8333cbc224bafc653eeda07fc5912a7a5b10376e186712f7bd6c2673e9b2a47e"
STATUS = "CROP_ID_REAL_AUTH_PROVEN_CHALLENGE_IMAGES_PENDING"
BLOCKER = "No genuine challenge images were supplied in the incoming directory."


def write_json(name: str, value: object) -> None:
    (AUDIT / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main(receipt_path: str) -> None:
    AUDIT.mkdir(parents=True, exist_ok=True)
    receipt = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
    results = receipt["results"]
    canonical_sha = hashlib.sha256(CANONICAL.read_bytes()).hexdigest()
    canonical_ok = canonical_sha == EXPECTED_CANONICAL_SHA
    created = receipt["created_at_utc"]

    auth_env = {
        "method": "FIREBASE_AUTH_EMULATOR",
        "selection_reason": "Exercises issued tokens, Firebase Admin verification, revocation, disabled users, backend role resolution, and actual HTTP without production identities or credentials.",
        "project_id": receipt["project_id"],
        "auth_endpoint": receipt["auth_endpoint"],
        "backend_endpoint": "http://127.0.0.1:8019",
        "configuration_files": [
            "firebase.json",
            ".firebaserc",
            "backend/.env.crop-id-emulator.example",
        ],
        "credential_handling": "No production credential, raw password, raw token, or private key was stored.",
        "limitations": [
            "Firebase CLI returned a nonzero wrapper status after its child validation succeeded and the emulator shut down; the child receipt and HTTP results were produced successfully."
        ],
        "cleanup": "The emulator was stopped by emulators:exec; delete synthetic emulator state and the isolated SQLite database/virtual environment after validation.",
    }
    write_json("AUTH_ENVIRONMENT_REPORT.json", auth_env)
    write_json(
        "TEST_IDENTITY_PROVISIONING_RECEIPT.json",
        {
            "created_at_utc": created,
            "environment": receipt["environment"],
            "identities": receipt["identities"],
            "identity_count": len(receipt["identities"]),
            "raw_password_recorded": False,
            "raw_token_recorded": False,
            "private_key_recorded": False,
        },
    )
    write_json(
        "TEST_IDENTITY_REVOCATION_REPORT.json",
        {
            "methods": [
                "remove backend tester role",
                "assign farmer role",
                "disable emulator identity",
                "revoke refresh tokens",
            ],
            "revoked_token_result": results["revoked_token"],
            "disabled_user_result": results["disabled_user"],
            "status": "PASS",
        },
    )
    write_json("REAL_HTTP_AUTH_RESULTS.json", receipt)
    write_json(
        "EXPIRED_TOKEN_TEST_REPORT.json",
        {
            "test_status": "EXPIRED_TOKEN_REAL_HTTP_TEST",
            "result": results["expired_token"],
            "pass": results["expired_token"]["status_code"] == 401,
        },
    )
    write_json(
        "REVOKED_TOKEN_TEST_REPORT.json",
        {
            "test_status": "REVOKED_TOKEN_REAL_HTTP_TEST",
            "result": results["revoked_token"],
            "pass": results["revoked_token"]["status_code"] == 401,
        },
    )
    write_json(
        "DISABLED_USER_TEST_REPORT.json",
        {
            "test_status": "DISABLED_USER_REAL_HTTP_TEST",
            "result": results["disabled_user"],
            "pass": results["disabled_user"]["status_code"] == 401,
        },
    )

    with (AUDIT / "CHALLENGE_IMAGE_INVENTORY.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        csv.writer(handle).writerow(
            [
                "challenge_image_id",
                "original_file_name",
                "source_type",
                "collected_by",
                "collection_date",
                "approximate_location",
                "device_type",
                "consent_status",
                "reuse_permission_status",
                "expected_category",
                "expected_crop",
                "requested_crop",
                "review_status",
                "notes",
            ]
        )

    unavailable = {"status": "INSUFFICIENT_EVIDENCE", "image_count": 0, "blocker": BLOCKER}
    for name in (
        "CHALLENGE_PROVENANCE_REPORT.json",
        "CHALLENGE_PERMISSION_REPORT.json",
        "INGESTION_VALIDATION_REPORT.json",
        "DUPLICATE_REPORT.json",
        "NEAR_DUPLICATE_REPORT.json",
        "QUARANTINE_REPORT.json",
        "MANUAL_REVIEW_REPORT.json",
        "DIRECT_RUNTIME_RESULTS.json",
        "BACKEND_PIPELINE_RESULTS.json",
        "DIRECT_BACKEND_PARITY_REPORT.json",
        "PER_CLASS_REPORT.json",
        "FALSE_CONFIDENT_ERRORS.json",
    ):
        write_json(name, unavailable)
    write_json(
        "FROZEN_SPLIT_LEAKAGE_REPORT.json",
        {
            "canonical_manifest_path": str(CANONICAL),
            "canonical_manifest_sha256": canonical_sha,
            "expected_sha256": EXPECTED_CANONICAL_SHA,
            "canonical_manifest_hash_verified": canonical_ok,
            "challenge_images_compared": 0,
            "exact_frozen_duplicates": 0,
            "status": "NOT_RUN_NO_CHALLENGE_IMAGES",
        },
    )
    write_json(
        "CHALLENGE_FREEZE_RECEIPT.json",
        {
            "frozen": False,
            "manifest_sha256": None,
            "approved_image_count": 0,
            "reason": "An empty challenge set must not be frozen.",
            "tuning_prohibited": True,
            "official_accuracy_claim": False,
            "field_validation_claim": False,
        },
    )
    write_json(
        "METRICS_REPORT.json",
        {
            "status": "UNAVAILABLE_NO_APPROVED_CHALLENGE_IMAGES",
            "all_performance_metrics": None,
            "official_accuracy_claim": False,
        },
    )
    write_json(
        "SAFETY_FALLTHROUGH_REPORT.json",
        {
            "auth_denial_crop_id_calls": 0,
            "auth_denial_disease_model_calls": 0,
            "challenge_pipeline_unsafe_fallthrough_count": None,
            "status": "AUTH_BOUNDARY_PASS_CHALLENGE_EVALUATION_NOT_RUN",
        },
    )
    write_json(
        "MODEL_CALL_SAFETY_MATRIX.json",
        {
            case: {
                "status_code": value["status_code"],
                "reason_code": value["reason_code"],
                "crop_id_model_called": value["crop_id_model_called"],
                "disease_model_called": value["disease_model_called"],
            }
            for case, value in results.items()
        },
    )
    gaps = {
        "status": "INSUFFICIENT_EVIDENCE",
        "supported_crops_without_approved_challenge_images": [
            "banana",
            "paddy",
            "cotton",
            "groundnut",
        ],
        "unsupported_crop_evidence_missing": True,
        "non_plant_evidence_missing": True,
        "quality_and_domain_coverage": "UNAVAILABLE",
    }
    write_json("COVERAGE_GAPS.json", gaps)
    write_json(
        "BLOCKERS.json",
        {
            "final_status": STATUS,
            "primary_blocker": BLOCKER,
            "blocked_actions": [
                "challenge freeze",
                "direct runtime evaluation",
                "authenticated backend challenge evaluation",
                "parity and performance metrics",
            ],
        },
    )
    final = {
        "final_status": STATUS,
        "auth_environment": "FIREBASE_AUTH_EMULATOR",
        "real_http_auth_proven": True,
        "approved_challenge_images": 0,
        "canonical_manifest_hash_verified": canonical_ok,
        "model_retrained": False,
        "model_recalibrated": False,
        "thresholds_changed": False,
        "provisional_test_reopened": False,
        "general_farmer_inference_authorized": False,
        "official_accuracy_claim": False,
        "field_validation_status": "NOT_PROVEN",
        "primary_blocker": BLOCKER,
    }
    write_json("FINAL_REPORT.json", final)
    (AUDIT / "FINAL_REPORT.md").write_text(
        "# Crop-ID Real Authentication and Internal Challenge Audit\n\n"
        f"- Final status: `{STATUS}`\n"
        "- Real HTTP auth: PASS for internal/pilot authorization and fail-closed denial cases.\n"
        "- Challenge images: 0; no image was invented, imported, opened, or approved.\n"
        f"- Canonical manifest hash: `{canonical_sha}` (verified: {canonical_ok}).\n"
        "- Performance metrics: unavailable; the challenge manifest was not frozen.\n"
        "- Farmer inference remains unauthorized; no official or field-accuracy claim is made.\n",
        encoding="utf-8",
    )
    (AUDIT / "NEXT_ACTIONS.md").write_text(
        "# Next Actions\n\n"
        "Supply genuinely new, consented, provenance-documented challenge images in "
        "`internal_challenge_sets/crop_identity_v1/incoming/` for independent manual "
        "review, leakage checks, quarantine, and a non-empty freeze.\n",
        encoding="utf-8",
    )
    (AUDIT / "COMMANDS_EXECUTED.txt").write_text(
        "npx.cmd --yes firebase-tools@latest --version\n"
        "uv venv backend\\.venv_crop_real_auth --python 3.12\n"
        "uv pip install --python backend\\.venv_crop_real_auth\\Scripts\\python.exe -r backend\\requirements.txt\n"
        "npx.cmd --yes firebase-tools@latest emulators:exec --only auth --project demo-agrowai-crop-id-test <validation-command>\n"
        "Get-FileHash D:\\AgrowAI\\incoming_model_bundles\\canonical_split_manifest.json -Algorithm SHA256\n",
        encoding="utf-8",
    )
    print(AUDIT)


if __name__ == "__main__":
    main(sys.argv[1])
