# Single-owner admin access

Deploy the backend code supporting `ADMIN_OWNER_FIREBASE_UID` before enabling it.
On the production API service, set `ADMIN_OWNER_FIREBASE_UID` to the verified
Firebase UID of the existing active Owner account. Keep `ADMIN_REQUIRE_MFA=true`.
Do not put this setting in the mobile or admin-web service.

When configured, the backend requires both the exact UID and the Owner role.
It checks this during web-session creation and on subsequent admin requests,
including requests with previously issued cookies or bearer tokens. It also
blocks creation and acceptance of admin invitations. It does not delete users
or alter farmer access. Empty/unset retains the existing multi-admin RBAC policy.

After rollout, verify the owner can sign in with MFA, read `/api/v1/admin/me`
and procurement, and that an unrelated authenticated account receives denial.
Public access to the sign-in page does not provide dashboard/API access.
This is an account restriction, not device binding: protect the owner's password,
MFA, active browser sessions, and Firebase/Railway administrative access.

If the wrong UID locks out the owner, correct the setting through the trusted
Railway deployment account and restart/redeploy. Never disable MFA to recover.
