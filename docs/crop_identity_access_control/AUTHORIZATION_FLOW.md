# Authorization flow

```text
Bearer token received
  -> Firebase Admin cryptographic verification
  -> Firebase issuer/audience/expiry validation
  -> users.firebase_uid resolution
  -> active/non-deleted user validation
  -> user_roles + roles database resolution
  -> exactly one of internal_tester/pilot_tester
  -> controlled route authorization
  -> upload and image gates
  -> crop-ID inference
  -> matching disease adapter
```

Firebase verification failures are authentication failures. Backend role
lookup failure is `AUTHORIZATION_UNAVAILABLE`. Farmer, missing, unknown, or
conflicting controlled roles return `TESTER_ROLE_REQUIRED`. Client role fields
are ignored.
