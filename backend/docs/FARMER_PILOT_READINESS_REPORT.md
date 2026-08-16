# AgrowAI farmer pilot deployment readiness

Assessment: **NOT_READY**

This report records locally verified software evidence only. It does not claim a
cloud deployment, field validation, legal approval, expert approval, official
accuracy, or successful farmer use.

## 1. Cloud deployment

Production artifacts now exist:

- `Dockerfile.production` runs as an unprivileged user.
- `docker-compose.production.yml` provides API/worker startup, migration, frozen
  read-only model mounting and readiness checks.
- `.env.production.example` contains placeholders only.
- Production boot refuses wildcard CORS/trusted hosts, debug mode, localhost
  database/Redis/API targets, mock OTP and missing Firebase Admin configuration.
- Android release configuration refuses localhost/emulator endpoints and non-HTTPS
  API URLs.

No public cloud service or HTTPS domain was deployed during this work. Public API
URL: **not available**.

## 2. OTP

Verified in source/tests:

- Android package is `com.agrowai.app`.
- `google-services.json` project package matches `com.agrowai.app`.
- Release upload certificate:
  - SHA-1: `A7:59:10:2E:FE:CC:2F:5A:B6:F2:E3:5E:45:24:A6:DA:4B:23:CF:14`
  - SHA-256: `50:CF:9C:02:D7:0B:67:A1:B9:B8:F6:CA:06:6E:3A:09:0B:97:7B:49:87:7E:44:A6:99:51:B7:CA:AB:06:A7:6E`
- Indian phone input is normalized to `+91`.
- Native Firebase Phone Auth uses Play Integrity and maps invalid phone, quota,
  network and attestation failures to visible localized errors.
- Backend verifies Firebase ID tokens and rotates/revokes server sessions.

Blocked external evidence:

- Firebase console Phone Auth enabled state
- India SMS region policy
- release SHA fingerprints registered in Firebase
- Play Integrity acceptance for the release build
- physical OTP success on two devices
- expiry/resend behavior against the real provider

No single OTP root cause can be claimed until those console/device checks are run.

## 3. Farmer dashboard and history

Existing farmer modules provide profile, farms, produce listings/history,
notifications and feature-specific records. A single consolidated dashboard
containing every requested disease, nutrient, satellite, listing, offer and
notification history with uniform `created time`, `status`, and `source` has not
been demonstrated. This gate remains blocked.

## 4. Sell My Produce

An authenticated ownership-scoped produce workflow exists with crop, farm,
variety, quantity, unit, harvest date, optional farmer asking price, images,
notes, location fields, status history and verified market-price provenance.
Farmers are not charged.

The current lifecycle is the pre-existing procurement-planning lifecycle
(`draft`, `submitted`, `planned`, `harvested`, `fulfilled`, `withdrawn`,
`expired`). It does not yet implement the requested buyer-offer state machine
(`UNDER_REVIEW` through `COMPLETED`) or explicit contact-sharing consent.
Therefore the requested workflow is not release-complete.

## 5. Admin/buyer dashboard

Authenticated backend admin routes, server-side RBAC, procurement filters,
status updates, broadcasts, audit logs and analytics exist. The current client
also contains sample/local fallback data and is not an independently deployed
admin web URL. `BUYER_OPERATOR` end-to-end authorization and the requested offer
creation/pickup/purchase/export workflow are not fully evidenced.

Admin dashboard URL: **not deployed**.

## 6. Notifications

The backend persists notifications with unread/read state, delivery logs,
deduplication and retry handling. A real FCM provider supports privacy-safe
Tamil/English push titles, data-only localization/deep-link keys and targeted
device tokens. Missing Firebase credentials honestly fall back to in-app-only
delivery.

No live FCM delivery from a submitted listing or admin offer was performed.

## 7. Branding

Not changed. Approved logo and splash assets were not supplied.

## 8. Disease and nutrient safety

- The frozen classifier remains restricted to paddy/rice, cotton and groundnut.
- Unsupported crops are rejected before model loading/inference.
- Possible nutrient deficiency offers a separate assessment and transfers only
  allowlisted, consented context.
- Disease output is never reused as nutrient truth.

Frozen model checkpoint, temperature, confidence threshold, calibration and
sealed metrics were not modified.

## 9. Satellite

The UI shows an unavailable/retry state and does not fabricate metrics. The
Sentinel/Copernicus acquisition branch remains a placeholder, so Satellite
Intelligence is **unavailable for the pilot**.

## 10. Privacy and compliance

Image-storage consent exists in the disease workflow and sensitive image/token
content is excluded from logs. However, clickable reviewed privacy/terms text,
contact-sharing consent, farm-location/satellite consent, account deletion,
data-deletion request, export and an approved retention schedule are not complete.
Legal compliance is not claimed and legal review remains required.

## 11. Security and observability

Locally verified controls include Firebase token validation, backend RBAC,
request IDs, security headers, body-size limits, rate limiting, structured
logging, guarded metrics, DB/Redis/model readiness, FCM delivery tracking and
backend Sentry integration when configured.

Open gates:

- TLS ingress and public security-header inspection
- managed secret store and database least-privilege evidence
- private object-storage policy verification
- Android crash-reporting delivery
- backup/restore and alert drills
- live OTP/FCM error-category monitoring
- 51 moderate transitive `uuid` advisories in the Expo toolchain; npm reports no
  fix and no high/critical finding at the selected audit gate

## 12. Test evidence

- TypeScript: PASS
- Focused Android tests: 205 PASS
- Complete Android Jest: 551 PASS
- Focused backend tests: 77 PASS
- Ruff on changed backend files: PASS
- Python compile: PASS
- Production Compose static validation: PASS
- Release signing report: PASS
- Database migration to head: recorded separately in the execution handoff
- Complete backend pytest and release APK rebuild: recorded separately in the
  execution handoff

Physical-device OTP, supported-crop disease, production offline/retry, FCM and
rapid-navigation validation remain external gates.

## 13. Pilot release gate

The following prevent `PILOT_READY`:

1. No developer-independent cloud API or public HTTPS domain.
2. No verified production database, Redis, object storage or secret manager.
3. No two-device OTP evidence.
4. No tested database restore.
5. No APK proven to communicate only with the production API.
6. Requested buyer-offer lifecycle and contact consent are incomplete.
7. No live listing-to-admin-to-farmer FCM evidence.
8. Privacy, deletion, export and retention flows are incomplete.
9. Crash monitoring has not been verified.
10. Satellite acquisition is unavailable.
11. No signed physical pilot checklist or legal review.

## 14. Final status

**NOT_READY**
