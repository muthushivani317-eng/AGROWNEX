# Android Signing Key Management

## Scope

The Android `release`, `localStandalone`, and `internalTesting` variants all use the `production` signing configuration. Only `debug` may use `android/app/debug.keystore`. Release-derived builds fail before packaging when production signing is missing or points to the Android debug key.

## Credential ownership

The production upload keystore is an offline-controlled release asset. The raw `.jks` file and its passwords must never be stored in Git, repository artifacts, build logs, chat, issue trackers, developer `.env` files, or APK evidence folders. Repository ignore rules cover `.jks` and `.keystore` files.

The CI copy is held in the protected GitHub Environment named `production-signing`:

| Secret | Value |
|---|---|
| `AGROWAI_RELEASE_KEYSTORE_BASE64` | Base64 representation of the binary upload keystore |
| `AGROWAI_RELEASE_STORE_PASSWORD` | Keystore password |
| `AGROWAI_RELEASE_KEY_ALIAS` | Non-debug upload key alias |
| `AGROWAI_RELEASE_KEY_PASSWORD` | Private-key password |

The same environment also holds required public build configuration secrets. Configure required reviewers and restrict deployment branches for this environment. Do not make signing secrets available to pull-request workflows or forked code.

## Initial creation and custody

1. An authorized founder/release custodian creates the upload key on a trusted offline workstation using Android `keytool`, with a unique alias and strong generated passwords.
2. Two authorized custodians verify and record the certificate SHA-256 fingerprint independently.
3. Store two encrypted backups in separate controlled locations. Record owners, creation time, certificate fingerprint and recovery-test date; do not record passwords beside the backups.
4. Base64-encode the binary only for entry into the protected CI secret. Delete transient plaintext/base64 working copies after verification.
5. Add environment reviewers and branch restrictions before the first signed workflow run.

This repository does not generate, contain or rotate the real signing key.

## Build contract

Gradle reads these runtime-only variables:

```text
AGROWAI_RELEASE_STORE_FILE
AGROWAI_RELEASE_STORE_PASSWORD
AGROWAI_RELEASE_KEY_ALIAS
AGROWAI_RELEASE_KEY_PASSWORD
```

`.github/workflows/android-signed-build.yml` reconstructs the keystore with mode `0600`, validates it, builds one explicitly selected variant, deletes it in an `always()` step and retains the resulting CI artifact for seven days. Secrets are never printed.

Local release-derived builds require an authorized, temporary keystore path and the same four environment variables. Routine development must use the `debug` variant instead.

## Rotation and incident response

- Rotate the upload key according to the app-store key-reset process, not by silently replacing it.
- If bytes or passwords may have been exposed, stop signed builds, revoke CI environment access, preserve audit logs, notify both custodians, and begin the store-provider reset/rotation process.
- Update the recorded certificate fingerprint and CI secrets together. Run a signed internal artifact and verify its signer before resuming release work.
- Test backup recovery at least annually and whenever custodians change.

## Verification record

For every release, retain the workflow run ID, commit SHA, variant, APK/AAB SHA-256 and signing-certificate SHA-256. Never retain the keystore or passwords in the verification report.
