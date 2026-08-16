# Navigation defects

## Confirmed root cause

`useStartupRouteGuard` previously computed `shouldReplace` using `!inAuth`. For an authenticated user, every legitimate root-stack destination such as `/disease`, `/weather`, or `/schemes` is outside the auth group, so it was immediately replaced with `/(tabs)`, appearing to return to Home.

## Repair

- Authenticated users are redirected only when they remain inside the auth group.
- Unauthenticated users are still redirected away from protected routes.
- Home paths are centralized in `HOME_FEATURE_ROUTES`.
- Every visible action has a non-root explicit destination.
- Regression tests cover the affected stack routes and signed-out protection.
