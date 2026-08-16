# Tester role contract

`farmer`, `internal_tester`, and `pilot_tester` are backend roles stored in
`roles` and assigned through `user_roles`.

- `farmer`: cannot call crop-ID-backed disease inference.
- `internal_tester`: revocable controlled internal evaluation access.
- `pilot_tester`: revocable controlled pilot evaluation access.

Tester roles are not administrator roles and grant no model, threshold,
runtime-file, or policy-management permission. Client JSON, query parameters,
headers other than the verified bearer token, and mobile state never determine
authorization. Exactly one controlled tester role must resolve; missing,
unknown, or conflicting controlled roles fail closed.

The runtime is public-dataset provisional. Field performance, non-plant
rejection, and farmer-photo robustness are unproven. No official accuracy claim
is permitted.
