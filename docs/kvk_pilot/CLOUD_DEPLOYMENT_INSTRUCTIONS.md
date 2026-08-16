# Public HTTPS Backend Deployment Gate

1. Revoke the compromised Firebase key and store a least-privilege replacement in
   a cloud secret manager.
2. Select a real host and configure FastAPI, PostgreSQL, Redis, persistent model
   storage, health checks, restart policy, trusted hosts, explicit CORS, TLS, and
   redacted logs.
3. Install and verify the canonical six runtime packages without changing them.
4. Configure server-only Gemini and Firebase Admin secrets.
5. Set `PUBLIC_API_URL=https://<real-public-host>`,
   `EXPO_PUBLIC_API_BASE_URL=https://<real-public-host>/api/v1`, and
   `EXPO_PUBLIC_DIAGNOSIS_API_BASE_URL=https://<real-public-host>`.
6. Add a `kvkPilot` internal-distribution APK profile only after the hostname is
   known. Run release validation, external authenticated tests, phone tests, and
   a laptop-off test.
7. Build with `eas build --platform android --profile kvkPilot`.

Placeholders must be replaced with a real verified hostname; this document does
not claim deployment.
