# Root-cause assessment

Confirmed repository deployment defect: `backend/Dockerfile.production` started Uvicorn directly and never invoked Alembic. The repository head is `ba143fe612a8`; `users.last_login` is introduced by `ba143fe612a6`. The OTP session path queries a full `User` row and then updates `last_login`, so a production database behind that migration fails before session establishment.

This explains why `/ready` can pass: readiness performs connectivity checks, not an auth-schema compatibility check.

The precise production exception class/SQLSTATE remains unconfirmed because authenticated Railway logs were unavailable. The change is a safe deployment correction independent of whether the observed exception is ultimately `UndefinedColumn` or another unapplied-migration failure.
