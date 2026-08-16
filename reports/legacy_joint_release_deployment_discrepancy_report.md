# Legacy Joint Release-Decision / Deployment Discrepancy — Factual Investigation

Investigation date: 2026-08-07 (Asia/Calcutta)

Scope: repository and local runtime evidence only. No live functionality, configuration, data, or gates were changed.

## 1. Timeline

### Decision record

`backend/model_artifacts/legacy_joint_v1_crop_constrained/reports/crop_constrained_recalibration_decision.json:2-12` says verbatim:

```json
"decision": "READY_FOR_BACKEND_INTEGRATION"
"app_enablement_allowed": false
"backend_integration_performed": false
"provisional_test_opened": false
```

The file contains no embedded timestamp. Its NTFS metadata is:

- last-write time: **2026-07-27 21:04:29 local time**;
- creation time: **2026-07-27 21:06:25 local time**.

The companion report says `Final decision: **READY_FOR_BACKEND_INTEGRATION**` at `backend/model_artifacts/legacy_joint_v1_crop_constrained/reports/crop_constrained_recalibration_report.md:3`, and says `Provisional-test material was not opened or used.` at lines 5-7.

### Backend integration

The first Git commit containing both the model bundle and live backend integration is:

```text
665c1ad92ae4c08652463daec455227db7a61bbd
AuthorDate/CommitDate: 2026-07-31T12:15:30+05:30
Subject: Prepare AgrowAI backend for controlled Render pilot
```

The parent of that commit contains neither `backend/app/legacy_joint/` nor `backend/model_artifacts/legacy_joint_v1_crop_constrained/`. Commit `665c1ad9` adds both directories, adds `backend/app/legacy_joint/api_router.py`, and adds `api_router.include_router(legacy_joint_router)` at `backend/app/api/v1/router.py:53`. Git blame attributes both the route inclusion and the verifier's decision handling to the same commit and timestamp.

The new files' local metadata further orders the uncommitted creation work:

- decision JSON last written: **2026-07-27 21:04:29**;
- `backend/app/legacy_joint/artifacts.py` created: **2026-07-27 21:08:09**;
- `backend/app/legacy_joint/runtime.py` created: **2026-07-27 21:08:11**, last written 21:17:27;
- `backend/app/legacy_joint/api_router.py` created: **2026-07-27 21:08:14**.

The live path is explicit:

- `backend/app/legacy_joint/api_router.py:19-20` creates the `/disease` router and shared runtime;
- lines 76-80 register `/disease/paddy/predict`, `/disease/cotton/predict`, and `/disease/groundnut/predict`;
- lines 86-112 invoke `runtime.predict(...)` and return its diagnosis;
- `backend/app/api/v1/router.py:17,53` imports and mounts that router;
- `backend/app/main.py:38-41` verifies and loads the runtime during startup when `disease_model_required` is true;
- `backend/app/crop_identity/router.py:43-59` also dispatches confirmed paddy, cotton, and groundnut images into the same runtime in the controlled crop-identity path.

### Chronology finding

**The decision record was written before the backend implementation files, by the available local timestamps; the integration then occurred despite `app_enablement_allowed: false`.** Git cannot provide a finer ordering because the decision record and integration were committed together four days later. NTFS timestamps can be preserved by copying and therefore are weaker evidence than an independently timestamped commit, but no earlier Git tree contains either artifact.

The mobile repository is a nested Git repository. Its relevant integration files are not committed there: `config/cropCapabilities.ts` and `features/multiCropDiagnosis/adapters.ts` are untracked, and `features/disease/screens/DiseaseScreen.tsx` is modified relative to the mobile baseline commit `d3449f4e3bac0330351411a05ba292e9f52c9366` dated 2026-07-13T19:59:23+05:30. Consequently, Git provides no auditable commit date for the mobile wiring. Current source nevertheless routes those crops at `agrow-ai/features/disease/screens/DiseaseScreen.tsx:348-362` and `agrow-ai/features/multiCropDiagnosis/adapters.ts:71-103`.

## 2. Why it was enabled anyway

### Mechanism found

The bundle verifier reads the contradictory record but checks only its integration-ready value:

```python
decision = _json(root / "reports/crop_constrained_recalibration_decision.json")
if decision.get("decision") != "READY_FOR_BACKEND_INTEGRATION":
    raise LegacyJointArtifactError("INTEGRATION_DECISION_NOT_READY")
```

Source: `backend/app/legacy_joint/artifacts.py:85-87`.

It does **not** inspect `app_enablement_allowed`, `backend_integration_performed`, or `provisional_test_opened`. The integration test likewise asserts only `result["decision"] == "READY_FOR_BACKEND_INTEGRATION"` at `backend/tests/test_legacy_joint_integration.py:10-15`.

The capability registry explicitly enables availability while retaining a non-production status:

- `backend/app/modules/disease/capabilities.py:46-54`: paddy/rice, cotton, and groundnut are `DEPLOYED_RESEARCH_ONLY` with `disease_model_available` set to `True`;
- the same public object always sets `production_approved` to `False` at lines 34-43;
- `agrow-ai/config/cropCapabilities.ts:78-102` declares all three `AVAILABLE_FIELD_VALIDATION_IN_PROGRESS`, points them to `legacy_joint_backend`, and lists their live API routes;
- the mobile capability constructor sets `productionApproved: false` at `agrow-ai/config/cropCapabilities.ts:145-160`.

This code explains **how** the enablement occurs and labels its status, but it is not a separate approval or sign-off record.

### Authorization search result

No later decision JSON, approval, override flag, sign-off, PR record, explanatory note, or commit message authorizing app enablement was found in the repository. Searches covered tracked and current Markdown, JSON, YAML, Python, TypeScript, and TSX content for the model name, decision fields, crop names, status strings, and approval terms, plus both Git histories and commit bodies.

The only relevant backend commit subject is `Prepare AgrowAI backend for controlled Render pilot`; its commit body contains no authorization rationale. The current status constants (`DEPLOYED_RESEARCH_ONLY`, `AVAILABLE_FIELD_VALIDATION_IN_PROGRESS`, and `productionApproved: false`) do not supersede the decision file with an approval. Repository evidence therefore contains **no authorization explaining or superseding `app_enablement_allowed: false`**.

## 3. Actual exposure — real-farmer count

### What is instrumented

The live legacy-joint prediction handler at `backend/app/legacy_joint/api_router.py:79-112` authenticates, validates, predicts, and returns a response, but it does not open a database session or create a `DiseaseReport`. Its only persistence is the separate user-initiated feedback endpoint, which appends feedback JSONL at lines 114-120. No legacy-joint log files are present under `backend/model_artifacts/legacy_joint_v1_crop_constrained/logs/` in this checkout.

The general schema does contain `disease_reports`:

- table declaration: `backend/app/modules/disease/models.py:32-33`;
- crop, disease, confidence: lines 48-52;
- model identifier and raw response: lines 64-65;
- creation timestamp supplied by the shared timestamp mixin and database migration at `backend/migrations/versions/0005_disease_reports.py:60`.

However, that table is written by the separate general disease module, not by `backend/app/legacy_joint/api_router.py`. Therefore even a crop-filtered count from `disease_reports` would not establish how many legacy-joint requests were served, and it cannot produce an accept/abstain breakdown for this handler.

### Available database access

- No `DATABASE_URL` exists in the investigation process environment.
- `backend/.env` identifies only a Docker-network host named `db`, database `agrowai`, port 5432; no Docker runtime is available in this environment.
- The only local database artifact found is `backend/agrowai_local_test.db`, size **0 bytes**, last written **2026-07-27 22:50:46**.
- No safe production database connection was available, so no production query was executed.

### Counts

- total legacy-joint diagnoses served: **NOT DETERMINABLE FROM REPOSITORY EVIDENCE**;
- earliest timestamp: **NOT DETERMINABLE**;
- latest timestamp: **NOT DETERMINABLE**;
- crop breakdown: **NOT DETERMINABLE**;
- accepted/abstained breakdown: **NOT DETERMINABLE**.

Recovering these figures requires production HTTP access logs or observability events that identify the three route paths and response outcome, or a prediction-audit store added outside this repository before/during deployment. A read-only `disease_reports` query alone is insufficient because the live handler does not populate that table.

## 4. What the app tells farmers today

### Live mobile routing

`agrow-ai/features/disease/screens/DiseaseScreen.tsx:348-362` selects the legacy-joint adapter for paddy, cotton, and groundnut. `agrow-ai/features/multiCropDiagnosis/adapters.ts:71-103` posts the confirmed image to `/disease/{paddy|cotton|groundnut}/predict` and parses the response.

The backend supplies `qualitative_confidence`, `official_accuracy_claim: False`, and `field_validation_status: "IN_PROGRESS"` at `backend/app/legacy_joint/api_router.py:103-112`. The parser requires those fields at `agrow-ai/features/multiCropDiagnosis/responseParser.ts:55-73`, but the result card does not render the confidence or validation fields.

### Exact accepted-result copy

For an accepted result, `agrow-ai/features/disease/screens/DiseaseScreen.tsx:566-577` shows:

- title: the raw class ID with underscores replaced by spaces (`jointResult.class_id.replaceAll('_', ' ')`);
- explanation: **“Disease result accepted under the frozen crop-specific decision policy.”**
- button: **“Provide feedback”** from `agrow-ai/features/multiCropDiagnosis/components/DiagnosisStates.tsx:3-5`.

There is no displayed percentage, qualitative confidence, `IN_PROGRESS` status, `official_accuracy_claim`, held-out-validation warning, or legacy/research-only label in this accepted-result card.

### Exact uncertain-result copy

For an abstention, `agrow-ai/features/multiCropDiagnosis/components/DiagnosisStates.tsx:14-20` displays:

- **“முடிவு உறுதியற்றது”**
- **“A disease could not be identified reliably. The symptoms may also be related to crop nutrition or another condition. Change the selected crop or retake the photo.”**
- **“Retake photo”**
- **“Check Nutrient Symptoms”**

### Localization comparison

No legacy-joint-specific accepted, uncertain, validation-status, or disclaimer copy exists in `agrow-ai/localization/locales/en.ts` or `ta.ts`; the copy above is hard-coded in component source. The localization files do contain confidence copy for the separate Banana experience:

- English: `“Confidence”`, `“High”`, `“Moderate”`, `“Low”` at `agrow-ai/localization/locales/en.ts:2039-2042`;
- Tamil: `“நம்பக நிலை”`, `“உயர்”`, `“மிதமான”`, `“குறைவு”` at `agrow-ai/localization/locales/ta.ts:2019-2022`.

Thus legacy-joint is **not** presented with the same rendered confidence labels as Banana. It has generic accepted/uncertain wording and no user-visible statement that field validation is in progress or that the model is deployed research-only. The phrase “frozen crop-specific decision policy” describes the decision policy but does not state the model's validation status.

## 5. Risk summary — factual findings only

### (a) No held-out accuracy evidence

**Confirmed.** `backend/model_artifacts/legacy_joint_v1_crop_constrained/lineage/model_lineage.json:75-79` says:

```json
"development_used_for_reporting_only": true,
"calibration_used_for_temperature_and_threshold_selection": true,
"provisional_test_used": false
```

The report labels development output `DEVELOPMENT_ONLY_NOT_AN_OFFICIAL_ACCURACY_CLAIM` at `backend/model_artifacts/legacy_joint_v1_crop_constrained/reports/crop_constrained_recalibration_report.md:15,21,27`. No held-out test accuracy, per-class held-out precision/recall/F1, or held-out confusion matrix was found.

### (b) Unresolved release-record contradiction

**Confirmed.** The active verifier and router use a record that simultaneously says `READY_FOR_BACKEND_INTEGRATION` and `app_enablement_allowed: false`; no later repository authorization or superseding decision was found. The verifier checks the former and ignores the latter (`backend/app/legacy_joint/artifacts.py:85-93`).

### (c) No validation-status disclaimer distinguishing it in the UI

**Confirmed, with one qualification.** The backend response exposes `official_accuracy_claim: False` and `field_validation_status: "IN_PROGRESS"` (`backend/app/legacy_joint/api_router.py:103-112`), and capability code calls it `DEPLOYED_RESEARCH_ONLY`/`AVAILABLE_FIELD_VALIDATION_IN_PROGRESS`. The farmer-facing accepted card does not render any of those facts. Its only explanatory sentence is **“Disease result accepted under the frozen crop-specific decision policy.”** (`agrow-ai/features/disease/screens/DiseaseScreen.tsx:568-570`).

### Active abstention/confidence safety gate

**Confirmed active in the live prediction path.** `backend/app/legacy_joint/api_router.py:87-96` calls `runtime.predict`. In `backend/app/legacy_joint/runtime.py:121-137`, logits are crop-restricted before calibration and softmax; lines 127-132 calculate confidence and margin, apply both stored thresholds, and return `uncertain` with no class when the gate rejects. Lines 133-137 additionally reject cross-crop labels and emit only `high` or `moderate` for accepted outcomes.

The loaded thresholds are read from the verified crop policies at `backend/app/legacy_joint/runtime.py:59-81`. The recorded values are paddy confidence 0.75/margin 0.0, cotton 0.5/0.0, and groundnut 0.5/0.0 (`backend/tests/test_legacy_joint_integration.py:18-36`). This same `runtime.predict` method is used by both the authenticated live crop-specific routes and the controlled crop-identity dispatcher.

## OPEN QUESTIONS FOR FOUNDER DECISION

- Was app enablement authorized outside the repository (for example in Slack, email, a meeting, or a verbal founder decision)? No such authorization is present in repository evidence.
- Was `app_enablement_allowed: false` intended to remain authoritative after `READY_FOR_BACKEND_INTEGRATION`, or were those fields meant to represent different release stages? The record does not define their precedence.
- Were the filesystem timestamps preserved from an external artifact transfer, or do they represent the actual local creation sequence? Git committed the decision and integration together and cannot resolve this further.
- Which deployed backend revisions and dates first exposed the three routes to general farmers? Deployment-platform history is not stored in this repository.
- Do hosting, proxy, API-gateway, Sentry, or other observability systems retain route-level requests and response outcomes sufficient to calculate exposure? No such production logs are available in the checkout.
- If an external system does contain exposure records, what are the total, first/last timestamps, per-crop counts, and accepted/abstained counts? The current handler itself does not persist the data needed to answer these questions.
