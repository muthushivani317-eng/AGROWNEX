# Database migration audit

- Source head: `ba143fe612a8`.
- Auth base tables: `0001_create_users` and `0002_auth_profile_tables`.
- `users.last_login`: added by `ba143fe612a6`.
- Production startup before fix: Uvicorn only; no migration command.
- Production revision: unavailable without Railway database/CLI access.
- Schema match: unverified.
- Destructive-risk assessment: the change runs only forward, repository-defined Alembic upgrades. It does not run downgrade, stamp, drop, truncate, or manual SQL.

Deployment must fail closed if an upgrade cannot be applied. Production revision must be confirmed from deployment logs before claiming schema parity.
