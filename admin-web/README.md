# AgrowAI Admin Web

Separate responsive PWA for authorised AgrowAI owner and team accounts. It is not
part of the farmer application and never falls back to sample data.

## Local run

1. Copy `.env.example` to `.env.local` and supply the public Firebase Web values and API URL.
2. Set backend `ADMIN_WEB_ORIGINS=["http://localhost:4173"]` for local development.
3. Run `npm ci` and `npm run dev`.

The backend must be running with migrations applied. Browser authentication exchanges
the Firebase ID token for an HttpOnly session cookie; JavaScript does not retain the
Admin token. New team members enter the one-time invitation code supplied by the owner.

## First owner

There is no public Admin signup. After the intended owner has authenticated once and
exists in the backend `users` table, run from the backend deployment shell:

```powershell
python scripts/bootstrap_admin_owner.py --firebase-uid FIREBASE_UID
```

The command refuses to create a second owner. All later access is granted through the
owner-only Team & permissions page.

## Production deployment

- Deploy the backend migration before the PWA.
- Host the PWA separately, e.g. `https://admin.agrowai.in`.
- Set that exact URL in backend `ADMIN_WEB_ORIGINS` and `CORS_ORIGINS`.
- Set `ADMIN_SESSION_COOKIE_NAME=__Host-agrowai_admin` in production.
- Set all `VITE_*` values in the static-site build environment.
- Test one farmer account (must be denied), owner, each team role, and a suspended Admin.
- Never cache `/api`, farmer details, CRM, revenue, AI cost, or audit responses.
