# AgrowAI controlled-pilot deployment runbook

Status: **NOT_READY until every external gate in the readiness record is evidenced.**

## Deploy

1. Provision managed PostgreSQL, Redis, private object storage and a TLS-terminating
   ingress. Use least-privilege service identities.
2. Copy `.env.production.example` to the platform secret/configuration system.
   Do not create or commit `.env.production`.
3. Mount the already-frozen model directory read-only and set
   `MODEL_ARTIFACT_HOST_DIR`.
4. Run `docker compose -f docker-compose.production.yml run --rm api alembic upgrade head`.
5. Run `docker compose -f docker-compose.production.yml up -d`.
6. Run `python -m scripts.verify_model_inventory` in the immutable image and
   require successful `/healthz`, `/readyz`, and `/ready` before routing pilot traffic.
7. Build Android with `APP_ENV=production` and HTTPS `EXPO_PUBLIC_*` endpoints.

The public ingress must enforce HTTPS. Port 8000 remains bound to loopback so it
cannot bypass the ingress.

## Rollback

1. Stop routing new traffic to the failing revision.
2. Restore the previous immutable application image and the same frozen model mount.
3. Apply only a reviewed backward migration where one exists. Never run a destructive
   downgrade automatically.
4. Validate `/readyz`, `/ready`, authentication, supported-crop inference and notification
   delivery before restoring traffic.

## Backup and restore

- Run encrypted PostgreSQL backups at least daily with retention approved by the
  pilot data-retention owner.
- Enable object-storage versioning and lifecycle retention.
- Store backups outside the primary failure domain.
- Test restore into an isolated database before the pilot; record duration, row
  counts and reviewer sign-off.
- A backup schedule is not evidence of recoverability until that restore succeeds.

Example operator commands:

```sh
pg_dump --format=custom --no-owner --file=agrowai.dump "$DATABASE_URL"
pg_restore --clean --if-exists --no-owner --dbname="$RESTORE_DATABASE_URL" agrowai.dump
```

Never place credentials in shell history, logs, images, or this repository.

## External gates

- DNS and trusted TLS certificate
- Firebase Phone Auth and India SMS policy
- release certificate SHA-1/SHA-256 registered in Firebase
- two-device OTP verification
- FCM device registration and targeted delivery
- managed database backup and isolated restore
- error/crash monitoring alert delivery
- legal review of privacy, terms and retention text
- signed physical farmer-pilot checklist
