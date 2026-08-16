# Splash audit

- Native splash: configured by `expo-splash-screen` in `app.config.js` with `assets/images/splash-screen.png`, `resizeMode: cover`, and background `#F2DCA9`.
- Duplicate React splash: previously mounted from `app/_layout.tsx`; no longer mounted.
- Native hide contract: `preventAutoHideAsync` at module startup and a once-only `hideAsync` call after a visible React layout.
- The legacy custom splash component remains unmounted. Its image has explicit 100% width and height if it is ever reused, but it is not part of the release startup path.

The user-reported before screenshots were not present as local files in this task, so no before PNG was fabricated.
