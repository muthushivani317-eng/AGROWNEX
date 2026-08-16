# Phase 0 — Android release signing

## Outcome

Source implementation and automated verification are complete. Operational activation remains gated on the release custodian provisioning the real production upload key in the protected `production-signing` GitHub Environment and executing the signed-build workflow. No production key or signed production artifact was created in this repository.

Phase 1 was not started.

## Implemented controls

- `agrow-ai/android/app/build.gradle` uses the external `production` signing configuration for `release`, `localStandalone`, and `internalTesting`. Only `debug` uses the debug keystore.
- Signing credentials are accepted only through the four `AGROWAI_RELEASE_*` environment variables (or equivalent Gradle properties).
- `validateProductionSigning` fails closed when credentials are missing, the keystore does not exist, or the file/alias identifies the standard Android debug key.
- Every release-derived assemble, bundle, and pre-build task depends on signing validation.
- `.github/workflows/android-signed-build.yml` performs a manually selected signed build through the protected `production-signing` environment, decodes the key only for the job, removes it on every exit path, and retains only the APK output.
- `agrow-ai/docs/ANDROID_SIGNING_KEY_MANAGEMENT.md` documents custody, protected secrets, offline backup, CI operation, rotation, incident response, and certificate verification.

## Automated tests

New tests: 4 in `agrow-ai/scripts/__tests__/release-signing.test.js`.

- Focused signing tests: **PASS** — 1 suite, 4 tests.
- Complete mobile Jest suite: **PASS** — 121 suites, 768 tests, 0 test failures (69.226 seconds).
- Complete backend suite: **PASS** — 872 passed, 1 skipped, 1 warning (175.11 seconds). The first invocation lacked the repository root on `PYTHONPATH`; the complete rerun used the correct repository import path.
- TypeScript check: **PASS**.
- Missing-secret Gradle validation: **PASS (expected rejection)** — `:app:validateProductionSigning` stopped the build and named all four required variables.
- Ephemeral non-debug credential validation: **PASS** — `:app:validateProductionSigning` completed successfully using a temporary locally generated test-only key; that key was deleted immediately afterward.

Full console evidence is saved in:

- `artifacts/phase0_mobile_tests.txt`
- `artifacts/phase0_backend_tests.txt`
- `artifacts/phase0_typecheck.txt`

## Required release-custodian actions

1. Create or select the real Android upload key offline under the organization’s documented custody process.
2. Configure the protected GitHub Environment `production-signing`, including required reviewers and branch/tag restrictions.
3. Add `AGROWAI_RELEASE_KEYSTORE_BASE64`, `AGROWAI_RELEASE_STORE_PASSWORD`, `AGROWAI_RELEASE_KEY_ALIAS`, and `AGROWAI_RELEASE_KEY_PASSWORD`, plus the documented public build configuration secrets.
4. Run the `Android signed build` workflow for the intended variant.
5. Verify and record the signing-certificate SHA-256 and APK SHA-256 before distribution.

Until those actions occur, production signing is intentionally unavailable and builds fail closed. Existing APKs are not evidence of this Phase 0 signing path.

## Repository state

Files staged: no. Files committed: no. Files pushed: no.
