# Railway log analysis

- Authenticated browser connection: unavailable in this session.
- Railway CLI: not installed or linked locally.
- Exact production stack trace: not captured.
- Real-device result supplied by the preceding validation: `/api/v1/auth/otp/verify` returned HTTP 500.
- Public `/health`: HTTP 200, `{"status":"ok"}`.
- Public `/ready`: HTTP 200; database, Redis, and Firebase reported ready.
- Safe invalid-token probe: HTTP 401.

No Firebase ID token, refresh token, OTP, full phone number, Firebase UID, credential, or database URL is recorded.
