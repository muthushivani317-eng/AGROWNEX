# Startup state machine

Implemented bounded flow:

`BOOTING -> STORAGE_INITIALIZING -> DATABASE_INITIALIZING -> AUTH_RESTORING -> ROUTE_RESOLVING -> READY`

Any step failure or the 15-second deadline enters `RECOVERABLE_ERROR`. Late asynchronous completions cannot overwrite a timeout. Every non-ready phase renders a dependency-free native-style loading or error screen. Native splash hiding uses a once-only guard on a laid-out React surface.

Routing outcomes:

- Fresh: language
- Language selected and signed out: login
- Successful OTP request: OTP entry
- Authenticated/incomplete profile: profile completion
- Authenticated/complete profile: tabs/main menu
