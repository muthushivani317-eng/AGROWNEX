# Adding a Verified Crop Runtime

Create `backend/model_artifacts/frozen_runtime/{crop_id}/` only after the crop's release evidence is approved. Required files:

```text
best.pt
class_to_index.json
index_to_class.json
preprocessing.json
temperature.json
selected_thresholds.json
abstention_policy.json
runtime_config.json
SHA256SUMS.txt
FROZEN_DECISION_RECORD.md
```

Then:

1. Validate `runtime_config.json` against `backend/app/crop_runtime/runtime_contract.schema.json`.
2. Confirm class IDs and preprocessing come from verified model evidence.
3. Recompute all hashes and verify the bundle.
4. Add parity and API-adapter test evidence.
5. Change the registry only after the runtime resolver passes.
6. Keep `official_accuracy_claim=false`.

Never copy another crop's configuration, use provisional-test outputs for tuning, or place sealed-test material in the runtime directory.
