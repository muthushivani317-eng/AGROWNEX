import {
  buildProfile,
  isFirebaseConfigured,
  type BuildProfile,
} from "@/config/env";
import { logger } from "@/lib/logger";

import { AuthError, type AuthProvider } from "../types";
import { firebaseAuthProvider } from "./firebaseAuthProvider";
import { mockAuthProvider } from "./mockAuthProvider";

/**
 * The active identity provider. Uses Firebase when configured, otherwise a local
 * mock so the app is fully runnable during development with no backend.
 */
const firebaseUnavailable = (): never => {
  throw new AuthError(
    "auth/firebase-not-configured",
    "auth.otpVerificationUnavailable",
  );
};

const unavailableAuthProvider: AuthProvider = {
  sendOtp: async () => firebaseUnavailable(),
  signInWithGoogle: async () => firebaseUnavailable(),
  signInWithApple: async () => firebaseUnavailable(),
  refreshToken: async () => firebaseUnavailable(),
  signOut: async () => firebaseUnavailable(),
};

/** Production must never silently fall back to fixed-code mock authentication. */
export function selectAuthProvider(
  firebaseConfigured: boolean,
  profile: BuildProfile,
): AuthProvider {
  if (firebaseConfigured) return firebaseAuthProvider;
  return profile === "production" ||
    profile === "internal_testing" ||
    profile === "kvk_field_test"
    ? unavailableAuthProvider
    : mockAuthProvider;
}

/**
 * Describe an absent Firebase configuration without implying that a release
 * build can use development authentication.
 */
export function authAvailabilityMessageKey(
  firebaseConfigured: boolean,
  profile: BuildProfile,
): "auth.devHint" | "auth.otpVerificationUnavailable" | null {
  if (firebaseConfigured) return null;
  return profile === "production" ||
    profile === "internal_testing" ||
    profile === "kvk_field_test"
    ? "auth.otpVerificationUnavailable"
    : "auth.devHint";
}

export const authProvider = selectAuthProvider(
  isFirebaseConfigured,
  buildProfile,
);

logger.info(
  "auth",
  `provider_category=${isFirebaseConfigured ? "firebase" : buildProfile === "production" || buildProfile === "internal_testing" || buildProfile === "kvk_field_test" ? "unavailable" : "development_mock"}`,
);
