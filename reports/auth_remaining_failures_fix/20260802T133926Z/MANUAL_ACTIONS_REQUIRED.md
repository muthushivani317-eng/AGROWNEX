# Manual actions required

1. Inspect sanitized Railway logs for the `/api/v1/auth/otp/verify` HTTP 500 near 2026-08-02 17:37:51–17:37:58 UTC. Do not copy tokens, phone numbers, OTPs, Firebase credentials, or user identifiers into reports.
2. In Railway, compare `alembic current` with `alembic heads`. If and only if the database is behind, apply the repository-approved `alembic upgrade head` release step.
3. Verify Firebase Admin credentials and project identity in Railway using secret-safe checks.
4. Verify required authentication tables, constraints, and role/seed state.
5. After the grounded backend fix, repeat OTP sign-in once and confirm session establishment; do not weaken App Verification or add a bypass.
