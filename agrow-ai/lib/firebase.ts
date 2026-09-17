import { getApp } from '@react-native-firebase/app';
import { getAuth, type Auth } from '@react-native-firebase/auth';

import { isFirebaseConfigured } from '@/config/env';

/**
 * Native Firebase access (@react-native-firebase).
 *
 * Unlike the Firebase JS SDK, the native SDK **auto-initialises the default app
 * at native startup** from the platform config files bundled by the config
 * plugin — `google-services.json` (Android) and `GoogleService-Info.plist`
 * (iOS). There is therefore no JS-side `initializeApp(env.firebase)` and no RN
 * persistence wrapper to configure; the native layer persists the session in the
 * platform keystore on its own.
 *
 * The `EXPO_PUBLIC_FIREBASE_*` env values are no longer used to boot the SDK.
 * They now only (a) gate mock-vs-real provider selection via
 * `isFirebaseConfigured` and (b) document the project for the backend/console
 * setup. The real credentials the native SDK actually uses live in
 * `google-services.json` / `GoogleService-Info.plist`.
 */
export function getFirebaseAuth(): Auth {
  if (!isFirebaseConfigured) {
    throw new Error('Firebase is not configured (missing EXPO_PUBLIC_FIREBASE_* env).');
  }
  // `getApp()` returns the auto-initialised default app; `getAuth()` returns the
  // process-wide singleton, so there is nothing to cache here.
  return getAuth(getApp());
}
