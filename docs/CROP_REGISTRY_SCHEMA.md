# Crop Registry Schema

The registry is stored at `backend/app/crop_runtime/crop_registry.json` and validated by Pydantic with unknown fields forbidden.

Supported statuses are exactly:

- `FROZEN_RUNTIME_READY`
- `MODEL_PIPELINE_PENDING`
- `MODEL_NOT_COMPLETED`
- `DATASET_UNRESOLVED`
- `LEGACY_JOINT_MODEL_AUDIT_REQUIRED`
- `DISABLED`

Non-ready entries cannot enable disease detection or declare a runtime path. Crop IDs and aliases must be unique. `official_accuracy_claim` is always `false`. Unverified Tamil text is explicitly `HUMAN_TRANSLATION_REVIEW_REQUIRED`.

The registry is configuration-backed; no model binary is stored in the database.

`last_verified_at` records successful verification of the complete runtime
contract at the configured local repository path. It is not the Colab
evaluation completion date and remains `null` until local verification occurs.
