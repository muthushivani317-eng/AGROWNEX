# Startup state machine

The deterministic phases are:

`BOOTING -> STORAGE_INITIALIZING -> DATABASE_INITIALIZING -> AUTH_RESTORING -> ROUTE_RESOLVING -> READY`

Any failed step or the 15-second deadline enters `RECOVERABLE_ERROR`. A late asynchronous completion cannot replace a timeout result. The failure screen offers Retry and a safe startup reset that clears only local authentication/onboarding/language startup state.

The native splash is hidden once, on the first laid-out React screen, including the recoverable-error and configuration-error screens. Fonts are non-blocking and use the system fallback if loading fails.
