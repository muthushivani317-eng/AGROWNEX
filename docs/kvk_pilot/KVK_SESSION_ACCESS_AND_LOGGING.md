# KVK supervised field-testing access and logging

This procedure is for supervised testing by an authorized controlled tester. It does not authorize general-farmer inference or any accuracy claim.

## Account preparation

1. Sign in once through the AgrowAI Android app using the phone number that will be used at the KVK. This creates the backend user associated with the verified Firebase identity.
2. Obtain that user's exact Firebase UID from the protected Firebase/backend administration surface. Do not place the UID, phone number, token, or OTP in source control or chat logs.
3. From the deployed backend environment, run the existing utility first without `--apply`:

```powershell
python backend/scripts/provision_controlled_tester.py `
  --firebase-uid "<exact-firebase-uid>" `
  --role kvk_reviewer `
  --receipt "<secure-private-path>/kvk-role-dry-run.json"
```

4. Review the hashed receipt, then repeat with `--apply`. Sign out and sign back in before testing so the new authorization is resolved cleanly.
5. The user logs in normally through Firebase phone authentication in the Android app. No special password, header, client flag, or alternate login endpoint grants the role.

## Field-test prediction log

Controlled predictions are appended as JSON Lines to:

```text
backend/logs/field_testing/controlled_predictions.jsonl
```

Set `AGROWAI_FIELD_TEST_LOG_PATH` to an absolute writable path before backend startup to redirect the file. Each row contains UTC timestamp, hashed tester subject, controlled role, crop, model ID, predicted class, confidence, and outcome. It contains no image, phone number, Firebase UID, token, OTP, location, or expert diagnosis.

The path is beneath the repository's ignored `backend/logs/` directory. This logger does not import a database session and does not write `disease_reports` or any other table.

Copy the JSONL file to secure session storage after testing. The KVK officer's independent diagnosis must be recorded separately and joined under the approved field protocol; this logger does not treat the model output as ground truth.

## Legacy-joint status

The unchanged release record has `app_enablement_allowed: false`, so legacy-joint remains unavailable. Do not edit that flag as part of session setup. The founder must choose between excluding legacy-joint from the session or separately approving development of a test-only override with an independent audit trail and no general application path.
