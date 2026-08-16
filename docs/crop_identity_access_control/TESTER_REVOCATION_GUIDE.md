# Tester revocation

Revoke controlled access by assigning `farmer` through the same utility:

```powershell
python backend/scripts/provision_controlled_tester.py `
  --firebase-uid "<explicit-user-id>" `
  --role farmer `
  --receipt "<secure-audit-output>.json" `
  --apply
```

This removes both controlled tester assignments. Subsequent requests resolve
roles from the database and are denied before upload decoding or model access.
