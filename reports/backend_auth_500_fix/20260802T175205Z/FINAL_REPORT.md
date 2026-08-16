# AgrowAI backend OTP verification HTTP 500 investigation

## Status

`FIX_PREPARED_DEPLOYMENT_AND_PRODUCTION_OTP_VALIDATION_PENDING`

The production service is live and reports PostgreSQL, Redis, and Firebase ready. An intentionally invalid Firebase token is rejected with HTTP 401, confirming fail-closed token validation. The repository production Dockerfile, however, launched Uvicorn without running Alembic migrations. The current `User` ORM selects and updates `users.last_login`, which exists only after migration `ba143fe612a6`.

The fix makes `alembic upgrade head` a mandatory startup gate before Uvicorn, removes identity data from auth logs, and adds secret-safe session-stage diagnostics. Focused auth tests pass 20/20. Ruff, Python compilation/import, and the Alembic graph pass. The complete backend suite is blocked during collection by a pre-existing missing `internal_challenge_sets` module.

The exact Railway exception and production Alembic revision could not be captured because neither an authenticated Railway browser connection nor Railway CLI is available in this session. Therefore the database drift remains strongly evidenced but not production-proven, and HTTP 200 is not claimed.

VERIFY AGAINST OFFICIAL DPDP REQUIREMENTS.

- ROOT_CAUSE=PRODUCTION_MIGRATION_STARTUP_GATE_MISSING; EXACT_RAILWAY_EXCEPTION_PENDING
- RAILWAY_EXCEPTION_CAPTURED=NO
- DATABASE_SCHEMA_MATCH=UNVERIFIED
- MIGRATIONS_APPLIED=PENDING_DEPLOYMENT
- FIREBASE_TOKEN_VERIFICATION=FAIL_CLOSED_CONFIRMED
- USER_UPSERT=LOCAL_TEST_PASS
- SESSION_CREATION=LOCAL_TEST_PASS
- OTP_VERIFY_ENDPOINT=PRODUCTION_HTTP_500_UNRESOLVED
- PRODUCTION_HTTP_STATUS=500_LAST_REAL_DEVICE_RESULT
- POST_LOGIN_NAVIGATION=BLOCKED
- SECRET_REDACTION=PASS
- FARMER_RELEASE_READINESS=NO
