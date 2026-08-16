# Disease Detection Remediation Final Report

Date: 2026-08-13  
Scope: disease workflow authorization, runtime readiness, mobile routing, error contracts, deployment checks, evaluation governance, promotion, and rollback.

## Executive outcome

The principal application failures were corrected. Disease detection no longer relies on contradictory mobile and backend availability flags. The authenticated backend capability response is now the decision authority for the mobile workflow, while every prediction endpoint independently enforces the same registry-aware controlled-role policy.

All six local disease runtimes, the six-class crop-identity runtime, its safety gate, and required inference dependencies load successfully in the project environment. This establishes operational readiness for controlled testing; it does not authorize general-farmer release and does not establish field accuracy.

No new accuracy percentage is claimed. The repository still lacks the independent, expert-labelled, farm-grouped field evidence required to demonstrate an accuracy improvement.

## Implemented and verified

### Capability and authorization

- Added authenticated `GET /api/v1/disease/capabilities` returning `{crops, crop_identification}`.
- Capability rows combine registry policy, cached executable readiness, exact user roles, build/release scope, adapter availability, supported classes, and sanitized blocker reasons.
- Exactly one controlled role is required; conflicting roles fail closed.
- Shared crop authorization policy is enforced by Banana, legacy joint, chilli, and redgram routes.
- Legacy paddy/cotton/groundnut are limited to internal tester or KVK reviewer while the controlled field-test session is active; pilot users are not advertised or accepted.
- Technical readiness no longer implies user authorization.
- Static mobile crop metadata cannot enable inference.

### Mobile workflow

- Replaced the hard-coded crop availability decision with the authenticated capability snapshot.
- Added fail-closed parsing and allowlisted adapter keys; server-provided URLs are never executed.
- Added explicit unavailable, unauthorized, integrity, runtime, offline, timeout, throttling, image-quality, and confirmation-token states in English and Tamil.
- Capability failures and zero-selectable-crop states now provide retry and back actions.
- Capabilities refetch on mount and are scoped by authenticated session.
- Replacing or retaking a photo invalidates image-bound confirmation state and restarts crop identification.
- Consumed or potentially consumed confirmation tokens are never retried; the UI requires a new photo and confirmation.

### Runtime and deployment readiness

- Added a fail-closed runtime inventory for NumPy, Pillow, ONNX, ONNX Runtime, Torch, TorchVision, all six disease runtimes, crop identity, and the crop-identity safety gate.
- Added technical readiness/inventory caches with explicit refresh and startup prewarming outside the event loop.
- Pilot readiness uses cached sanitized state and fails when an advertised runtime cannot load.
- Docker and CI invoke the model-inventory verifier.
- Standard HTTP exception envelopes preserve request IDs and protocol headers such as `Retry-After`.
- Missing dependencies/load failures are distinguished from artifact-integrity failures.

### ML measurement and lifecycle controls

- Added strict dataset, evaluation, prediction-event, promotion-policy, promotion-evidence, and model-registry contracts.
- Dataset validation checks licence, consent, expert review, privacy, hashes, duplicate samples, and cross-role leakage at source, farm, visit, plant, leaf, capture, and duplicate-family levels.
- Evaluation reports include confusion matrix, accuracy, balanced accuracy, macro/micro F1, per-class metrics, NLL, Brier score, ECE, abstention/coverage, accepted errors, latency percentiles, slices, OOD false accepts, and deterministic group-bootstrap confidence intervals.
- OOD records are evaluated separately and cannot contaminate in-distribution classification metrics.
- Promotion decisions bind the evaluation, model artifact, policy, dataset, and evidence hashes.
- Farmer promotion is impossible without a trusted external approval verifier and independent field evidence.
- The model registry validates closed state, uses a hash-chained audit trail, and supports safe rollback/disable drills without retraining.
- Prediction-event validation rejects unknown fields, nested sensitive data, malformed identifiers, invalid schema versions, and boolean values masquerading as numbers.

## Verification evidence

- Backend reviewed focused suite: **121 passed, 1 skipped**.
- Broad backend suite: **924 passed, 1 skipped, 5 failed initially**; all five failures were the paddy/rice canonical-ID regression introduced by authority consolidation. The mapping was corrected and its focused suite then passed **17, with 1 skipped**.
- Model inventory: every dependency, six disease runtimes, crop identity, and safety gate reported ready.
- Mobile reviewed focused suite: **97 passed**; TypeScript typecheck passed.
- Earlier integrated mobile capability suite: **135 passed**.
- Full mobile suite: **901 passed, 3 failed**. One disease source-contract failure was corrected. The other two failures concern pre-existing Home route-matrix and notification-copy expectations outside this disease scope.
- Hardened training-tools suite: **18 passed**; Ruff passed.
- Changed backend lint targets: passed after resolving formatting findings.

## Accuracy status

Engineering now makes accuracy measurable and promotion fail-closed, but it has not itself improved or proven field accuracy.

Current evidence limitations remain:

- Banana: no traceable held-out accuracy, dataset counts, split manifest, confusion matrix, or field result tied to the frozen bundle.
- Redgram: provisional accuracy 86.54%; sterility-mosaic recall 64.71%; leaf spot remains forced to abstain; coverage 48.08%.
- Chilli: provisional public-dataset accuracy 97.75% on 89 images, without independent farm/plant field grouping.
- Paddy: development macro F1 86.92%, but no untouched held-out field result.
- Cotton and groundnut: development-only perfect results on small sets, without independent field validation.
- Crop identity: strong sealed in-dataset metrics but unsafe excluded/OOD evidence; general-farmer release remains blocked.

## Required field programme before retraining or farmer promotion

1. Collect independently sourced, licensed, consented images grouped by district, farm, visit, plant, leaf, and multi-photo capture.
2. Obtain at least two independent expert reviews for ambiguous cases and adjudicate disagreements.
3. Prioritize Banana all classes, Redgram sterility mosaic and leaf spot, Paddy blast/brown leaf spot, and realistic Cotton/Groundnut confounders.
4. Build a locked OOD set containing unsupported crops, non-plants, mixed scenes, nutrient deficiencies, pest/mechanical damage, and poor-quality images.
5. Freeze train, development, calibration, and sealed field-test partitions by farm/visit/plant/capture group.
6. Pre-register per-class sample targets and promotion thresholds before opening the sealed test.
7. Train the current simple baseline first; then test class balancing, source-balanced batches, hard-negative mining, and realistic field augmentations.
8. Recalibrate temperature and per-class confidence/margin thresholds using calibration data only.
9. Promote through offline, internal, KVK pilot, and farmer stages only when executable evidence gates pass with no critical slice regression.

## Release decision

- Controlled internal/KVK testing: technically ready when the deployment inventory and authenticated capability response are green.
- General farmer inference: **BLOCKED**.
- Official or Tamil Nadu field accuracy claim: **NOT AUTHORIZED**.
- Accuracy improvement demonstrated by this change: **NO — field data and untouched evaluation are still required**.

## Remaining operational work

- Ensure the currently untracked six-class crop-identity artifact directory is included in the approved delivery mechanism; clean-checkout/container inventory now fails closed if it is absent.
- Run the real production container build and authenticated device E2E in the deployment environment.
- Resolve the two unrelated full-mobile-suite expectation failures if a completely green repository-wide Jest run is required.
- Connect governed prediction events and expert review labels to the production monitoring datastore/dashboard; the contracts and validators are implemented, but production data collection remains an operational deployment task.
