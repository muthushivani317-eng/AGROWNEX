# Production validation

Completed safe checks:

- `/health`: HTTP 200.
- `/ready`: HTTP 200; database, Redis, and Firebase report ready.
- `/api/v1/auth/otp/verify` with a deliberately invalid test token: HTTP 401.

Pending after deployment:

1. Confirm Alembic reaches `ba143fe612a8` in Railway logs.
2. Request a new Firebase OTP manually.
3. Verify it manually and exchange the fresh Firebase ID token.
4. Require HTTP 200 and a valid session response.
5. Confirm post-login navigation.
6. Confirm logs contain no token, OTP, full phone number, UID, credentials, or database URL.

The provisional HTTP 500 remains a failure until these steps pass.
