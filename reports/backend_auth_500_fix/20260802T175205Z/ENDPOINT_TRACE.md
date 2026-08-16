# Endpoint trace

`POST /api/v1/auth/otp/verify`

1. Pydantic validates `SocialLoginRequest`.
2. Firebase Admin verifies the ID token with revocation checking.
3. Claims supply the Firebase UID and optional phone number.
4. `UserRepository` locates or creates the user by unique Firebase UID.
5. The service updates `users.last_login`.
6. It records login history.
7. It creates a user session.
8. It persists a hashed refresh token.
9. It loads roles and an optional farmer profile.
10. The FastAPI database dependency commits; any exception rolls back.
11. `SessionOut` serializes the response.

New diagnostics record only the stable stage and exception class. They never record request tokens, claims, identities, or phone numbers.
