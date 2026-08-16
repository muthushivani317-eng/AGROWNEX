# Tester provisioning

Use the server-side dry-run-first utility with an explicit Firebase UID and one
explicit role:

```powershell
python backend/scripts/provision_controlled_tester.py `
  --firebase-uid "<explicit-user-id>" `
  --role internal_tester `
  --receipt "<secure-audit-output>.json"
```

Review the dry-run receipt, then repeat with `--apply`. Wildcards, unknown
users, unknown roles, and unseeded roles are refused. Receipts contain only a
hashed internal subject identifier and never tokens or secrets. No existing
farmer is promoted automatically.
