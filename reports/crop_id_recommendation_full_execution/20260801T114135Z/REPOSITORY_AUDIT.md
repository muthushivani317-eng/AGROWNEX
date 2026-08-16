# Repository Audit

Audit timestamp: `2026-08-01T11:41:35Z`

## Boundaries

- Parent/backend repository: `D:\AgrowAI\AgrowAi_app`
- Backend: `backend/` (FastAPI, PostgreSQL, Redis, Firebase Admin)
- Mobile repository: `agrow-ai/` (Expo prebuild/native Android, React Native Firebase)
- Training/notebooks: `training_tools/`, `notebooks/`
- Recommendation evidence: `recommendation_knowledge/`
- Deployment: `backend/Dockerfile.production`, `render.yaml`; Railway configuration is external and not locally queryable.

## Evidence-backed findings

- A frozen `crop_identity_v1` MobileNetV3 Small runtime exists for banana, paddy, cotton and groundnut only.
- Its checksum manifest and freeze/test receipts are present. The one-time provisional test was opened on 2026-07-29 and must not be reused for tuning.
- The receipt reports 618 public-dataset samples and explicitly records high shortcut risk, no official accuracy claim, and no farmer authorization.
- The runtime lacks `chilli`, `redgram`, `unknown_crop`, and `non_plant`. Independent non-plant rejection is explicitly unproven.
- Controlled backend routing is authenticated and limited to a controlled tester role; disease dispatch is blocked when crop identity abstains.
- Disease runtime registries exist for Banana, Paddy, Cotton and Groundnut; restricted Chilli and Redgram runtimes exist but farmer inference is disabled.
- The crop runtime registry is stale for Paddy/Cotton/Groundnut relative to the locally present legacy runtime evidence and must not be silently normalized.
- Recommendation source registry contains 52 sources, 22 marked eligible for final approval but still carrying human-confirmation notes.
- Review packets: Banana 5, Paddy 4, Cotton 3, Groundnut 2, Chilli 0, Redgram 0.
- `recommendation_knowledge/approved/` contains only a README: no approved runtime recommendation record exists.
- Mobile crop-ID/recommendation UI scaffolding exists but is untracked or mixed with extensive pre-existing changes; no live Railway E2E or laptop-off evidence was found.
- The parent and mobile worktrees contain substantial unrelated changes. Nothing was overwritten or staged by this audit.

## Security boundary

Untrusted image uploads cross the HTTP boundary. Existing crop-ID upload code enforces MIME allowlisting, a 12 MB cap, image decoding, and image-safety validation. Firebase role authorization protects controlled inference. The runtime response redacts checkpoint hashes. No raw image retention was observed in this route.

## Decision

`HIGHEST_VALID_STATUS=BLOCKED_INSUFFICIENT_DATA_AND_HUMAN_REVIEW`

Training an eight-class crop-ID model is blocked because four required classes have no approved leakage-safe dataset evidence. Recommendation deployment is blocked because no recommendation record is approved and Tamil review is not proven.
