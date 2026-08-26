# General Farmer Release Runbook

This checklist is a release gate. A successful APK build is necessary, but it
does not by itself authorize a production release. Record the operator, date,
Git commit, backend deployment ID, APK version code, and evidence link for each
completed item. Never paste secrets, OTPs, phone numbers, tokens, or farmer data
into the evidence log.

## 1. Release identity and artifact

- [ ] Mobile and backend release commits are reviewed, committed, and pushed.
- [ ] Production backend reports the same Git commit recorded for this release.
- [ ] PostgreSQL migrations upgrade successfully from a production snapshot in
      an isolated database; downgrade is tested only where the migration declares
      it safe.
- [ ] Mobile Jest, TypeScript, backend pytest, Ruff, Admin tests/build, and APK
      security inspection pass.
- [ ] APK/AAB is signed with the release key, has a unique version code, contains
      production API/Firebase configuration, and contains no mock/internal flags.
- [ ] Rollback artifacts for the previous mobile and backend versions are retained.

## 2. Firebase phone authentication

Capture screenshots or exported configuration evidence for every item:

- [ ] Phone is enabled in Firebase Authentication for the production project.
- [ ] India is allowed by the SMS region policy.
- [ ] Billing is active; daily SMS quota and budget alerts are configured.
- [ ] Release SHA-1 and SHA-256 fingerprints are registered.
- [ ] Play Integrity/App Check is enforced only after a verified staged rollout.
- [ ] A real-device OTP creates a Firebase credential, the backend exchanges it,
      and a farmer session can call an authenticated endpoint.
- [ ] Invalid, expired, reused, throttled, and quota-exhausted OTP paths show an
      honest retry/support message and do not create sessions.

## 3. Production dependency readiness

Before rollout, `/health` must be healthy and `/readyz` must report required
dependencies ready. Verify production configuration without printing values:

- [ ] PostgreSQL and Redis connections
- [ ] Weather provider and stale-data fallback labelling
- [ ] Market-price source, source timestamp, and unavailable state
- [ ] Satellite catalogue/render worker and public image-storage URL
- [ ] Disease, crop-identification, nutrient, and language/AI providers
- [ ] Push notifications, object storage, and scheduled/background workers
- [ ] Sentry/Crashlytics release identifiers and source-map/symbol upload

If a provider is absent, the feature must fail closed with an unavailable state.
Cached data must display its observation/source time; it must never be labelled
live merely because the screen was refreshed.

## 4. Agricultural safety gate

- [ ] Each enabled crop/model pair has an approved dataset, immutable model hash,
      validation report, crop-specific threshold, and named agricultural reviewer.
- [ ] Unsupported crops cannot reach generated operational recommendations.
- [ ] Low confidence, conflicting evidence, out-of-distribution images, and failed
      validation abstain or enter the access-controlled expert queue.
- [ ] Experts can record Confirmed, Corrected, Insufficient evidence, or Needs field
      inspection; corrections are audited and never silently rewrite the original.
- [ ] Recommendations and Tamil translations have qualified agricultural review.
- [ ] Production reporting calls model confidence “confidence,” never “accuracy,”
      unless measured against a labelled validation dataset.

The inaccessible or unverifiable Redgram runtime bundle is a hard gate: do not
enable or deploy it until its complete manifest verifies on the release machine.

## 5. Privacy, access, and deletion

- [ ] Farmer consent and privacy policy versions are published in English/Tamil.
- [ ] Consent collection records policy version, purpose, time, and actor.
- [ ] Farmer account closure is tested: it marks the account closed and revokes all
      refresh tokens/device sessions immediately.
- [ ] Closed accounts cannot create a new backend session with the same Firebase UID.
- [ ] A documented support process handles export, correction, and erasure requests.
- [ ] Admin roles use least privilege; farmer and suspended accounts receive no
      protected Admin data.
- [ ] Buyer-contact reveal and other sensitive reads are purpose-bound and audited.
- [ ] Application logs are sampled for phone numbers, tokens, image URLs, and other
      personal data before release.

Account closure is immediate access revocation, not an uncontrolled relational
database cascade. Transaction, consent, fraud-prevention, safety, and audit records
are retained only for the approved retention period. When that period expires, an
authorized privacy operator anonymizes personal fields using a reviewed job and
records only the request ID, scope, outcome, and timestamp.

## 6. Monitoring and alert thresholds

Configure alerts to an owned operations channel and test delivery:

- Backend availability below 99% over 5 minutes: critical.
- API 5xx rate above 2% for 5 minutes: critical.
- API p95 latency above 2 seconds for 10 minutes: warning.
- OTP backend exchange failures above 5% or Firebase quota/billing rejection: critical.
- Database connection exhaustion, migration mismatch, or readiness failure: critical.
- Satellite/image worker failures above 10% for 15 minutes: warning.
- AI provider quota/auth failure: critical; latency/cost anomaly: warning.
- Crash-free farmer sessions below the agreed SLO: halt staged rollout.

Never include raw phone numbers, tokens, free-text farmer notes, or buyer contacts
in alert payloads. Use internal request/user/listing IDs.

## 7. Backup and restore drill

1. Confirm encrypted automated PostgreSQL backups and retention in the provider.
2. Create an on-demand backup immediately before migration.
3. Restore the backup to a new isolated database, never over production.
4. Run migrations against the restored copy and execute read-only integrity checks:
   migration head, row-count ranges, foreign-key checks, and critical Admin queries.
5. Record restore duration and evidence without copying personal data into tickets.
6. Delete the isolated restore according to the approved temporary-data procedure.

No release proceeds without a successful restore drill within the agreed period.

## 8. Incident and rollback

1. Stop the staged rollout and disable only the affected feature using a reviewed,
   fail-closed configuration switch.
2. Preserve request IDs, deployment IDs, model hashes, and sanitized logs.
3. Roll the backend to the previous known-good Git deployment. Do not downgrade a
   database migration unless its reviewed downgrade is explicitly safe.
4. For a bad mobile release, halt distribution and publish a fixed higher-version
   build; already installed APKs cannot be remotely rolled back.
5. Notify affected farmers in plain English/Tamil when safety or personal data is
   involved, following the approved incident policy.
6. Complete a root-cause review and add a regression test before re-enabling.

## 9. Farmer support workflow

- Publish an in-app and public support contact with staffed hours and languages.
- Create categories for OTP/access, incorrect farm data, agricultural result,
  produce sale/payment, privacy/deletion, and safety emergency.
- Give every case an internal ID, severity, owner, next-action time, and audit trail.
- Agricultural disputes route to the permissioned expert queue; financial disputes
  route to procurement/finance; privacy requests route to the authorized owner.
- Support staff see only records required for the assigned case.

## Release decision

The release owner records one outcome: `GO`, `NO-GO`, or `STAGED-PILOT-ONLY`, with
open risks and compensating controls. Blank or unverifiable gates mean `NO-GO`.
