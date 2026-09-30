import {
  AppleAuthProvider,
  GoogleAuthProvider,
  PhoneAuthProvider,
  getIdTokenResult,
  signInWithCredential,
  signInWithPhoneNumber,
  signOut as fbSignOut,
  type ConfirmationResult,
  type User as FirebaseUser,
} from '@react-native-firebase/auth';

import { getFirebaseAuth } from '@/lib/firebase';
import {
  firebaseAuthErrorCategory,
  logger,
  reportFirebaseAuthErrorCategory,
} from '@/lib/logger';

import {
  AuthError,
  type AuthCredential,
  type AuthProvider,
  type RefreshedTokens,
} from '../types';

/**
 * Map a Firebase phone-auth failure to an {@link AuthError} whose message is a
 * translation key, so the UI can show a clear Tamil+English message instead of
 * failing silently. Unknown codes fall back to a generic "could not send" key.
 *
 * The native SDK (@react-native-firebase) normally verifies Android apps with
 * **Play Integrity**, but Firebase can use reCAPTCHA as a fallback. Keep both
 * paths mapped to a useful farmer-facing error instead of failing silently.
 */
function toSendOtpError(e: unknown): AuthError {
  if (e instanceof AuthError) return e;
  const code = (e as { code?: string } | null)?.code ?? '';
  const message = (e as { message?: string } | null)?.message;
  const category = reportFirebaseAuthErrorCategory('sendOtp', code, message);
  logger.warn('firebaseAuth.sendOtp', `error_category=${category}`);
  switch (category) {
    case 'auth/invalid-phone-number':
    case 'auth/missing-phone-number':
      return new AuthError(category, 'auth.invalidPhone');
    case 'auth/too-many-requests':
    case 'auth/quota-exceeded':
      return new AuthError(category, 'auth.otpQuotaExceeded');
    case 'auth/billing-not-enabled':
      return new AuthError(category, 'auth.otpBillingRequired');
    case 'auth/operation-not-allowed':
      return new AuthError(category, 'auth.otpPhoneSignInDisabled');
    case 'auth/network-request-failed':
      return new AuthError(category, 'auth.otpNetworkError');
    case 'auth/app-not-authorized':
    case 'auth/missing-client-identifier':
    case 'auth/invalid-app-credential':
    case 'auth/captcha-check-failed':
    case 'auth/invalid-recaptcha-token':
      // Native app attestation failed: Play Integrity / APNs not configured for
      // this build (e.g. SHA-256 fingerprint or Play Integrity API missing).
      return new AuthError(category, 'auth.otpVerificationUnavailable');
    default:
      return new AuthError(
        category === 'unknown' ? 'auth/otp-send-failed' : category,
        'auth.otpSendFailed',
      );
  }
}

function toConfirmOtpError(e: unknown): AuthError {
  if (e instanceof AuthError) return e;
  const nativeError = e as {
    code?: string;
    message?: string;
    nativeErrorCode?: string;
  } | null;
  const nativeCodeCategories: Readonly<Record<string, string>> = {
    ERROR_INVALID_VERIFICATION_CODE: 'auth/invalid-verification-code',
    ERROR_SESSION_EXPIRED: 'auth/session-expired',
    ERROR_TOO_MANY_REQUESTS: 'auth/too-many-requests',
    ERROR_QUOTA_EXCEEDED: 'auth/quota-exceeded',
    ERROR_NETWORK_REQUEST_FAILED: 'auth/network-request-failed',
    ERROR_APP_NOT_AUTHORIZED: 'auth/app-not-authorized',
    ERROR_INVALID_APP_CREDENTIAL: 'auth/invalid-app-credential',
    ERROR_CAPTCHA_CHECK_FAILED: 'auth/captcha-check-failed',
  };
  // React Native Firebase sometimes wraps the Android SDK error as
  // `auth/unknown` while retaining a stable native enum. Translate only a
  // fixed allowlist; never retain or report native messages, which may contain
  // the phone number or entered code.
  const nestedCategory = nativeError?.nativeErrorCode
    ? nativeCodeCategories[nativeError.nativeErrorCode]
    : undefined;
  const code = nestedCategory ?? nativeError?.code ?? '';
  const category = reportFirebaseAuthErrorCategory(
    'confirmOtp',
    code,
    nativeError?.message,
  );
  logger.warn('firebaseAuth.confirmOtp', `error_category=${category}`);
  switch (category) {
    case 'auth/invalid-verification-code':
    case 'auth/invalid-code':
      return new AuthError('auth/invalid-code', 'auth.otpIncorrect');
    case 'auth/session-expired':
    case 'auth/code-expired':
      return new AuthError(category, 'auth.otpCodeExpired');
    case 'auth/too-many-requests':
    case 'auth/quota-exceeded':
      return new AuthError(category, 'auth.otpQuotaExceeded');
    case 'auth/billing-not-enabled':
      return new AuthError(category, 'auth.otpBillingRequired');
    case 'auth/operation-not-allowed':
      return new AuthError(category, 'auth.otpPhoneSignInDisabled');
    case 'auth/network-request-failed':
      return new AuthError(category, 'auth.otpNetworkError');
    case 'auth/app-not-authorized':
    case 'auth/missing-client-identifier':
    case 'auth/invalid-app-credential':
    case 'auth/captcha-check-failed':
    case 'auth/invalid-recaptcha-token':
      return new AuthError(category, 'auth.otpVerificationUnavailable');
    default:
      return new AuthError(
        category === 'unknown' ? 'auth/otp-confirm-failed' : category,
        'auth.otpConfirmFailed',
      );
  }
}

async function toCredential(
  user: FirebaseUser,
  provider: AuthCredential['provider'],
): Promise<AuthCredential> {
  // Always mint a fresh token at the authentication boundary. Android phone
  // auth can auto-verify and expose `currentUser` before the Verify button is
  // pressed; reading its cached token here has produced tokens that the Admin
  // SDK rejects even though the OTP itself succeeded.
  const tokenResult = await getIdTokenResult(user, true);
  return {
    uid: user.uid,
    phone: user.phoneNumber,
    email: user.email,
    displayName: user.displayName,
    photoUrl: user.photoURL,
    idToken: tokenResult.token,
    // @react-native-firebase manages refresh tokens internally and does not
    // expose them — reading user.refreshToken throws. This field is unused by
    // this provider; do not restore `user.refreshToken` here.
    refreshToken: '',
    expiresAt: new Date(tokenResult.expirationTime).getTime(),
    provider,
  };
}

/**
 * Firebase codes that mean the session itself can no longer be renewed — the
 * farmer must sign in again. Anything else (a dropped connection, a rate
 * limit, an unrecognized native error) is transient: the caller should keep
 * the existing session and retry later rather than treat a network blip as
 * an invalid login (see farmer-release-readiness audit, 2026-08-18 — this
 * previously collapsed every refresh failure, including plain connectivity
 * loss, into the same "sign the farmer out" outcome).
 */
const SESSION_INVALID_CODES = new Set([
  'auth/user-token-expired',
  'auth/user-disabled',
  'auth/invalid-user-token',
  'auth/user-not-found',
  'auth/user-mismatch',
  'auth/invalid-user',
]);

/**
 * Real Firebase Authentication provider, backed by the **native** SDK
 * (`@react-native-firebase/auth`).
 *
 * Phone OTP uses the native `signInWithPhoneNumber`, which performs Play
 * Integrity verification natively — no reCAPTCHA, WebView or browser-script
 * loading (the failure mode that blocked the Firebase JS SDK in React Native).
 * Google and Apple keep obtaining their platform OIDC token via
 * `expo-auth-session` / `expo-apple-authentication` (unchanged), then exchange
 * it for a Firebase credential through the same native SDK so there is a single
 * source of auth truth — one `currentUser` for refresh and sign-out.
 */
export const firebaseAuthProvider: AuthProvider = {
  async sendOtp(phoneE164) {
    const auth = getFirebaseAuth();
    let confirmation: ConfirmationResult;
    try {
      // No ApplicationVerifier: the native SDK handles Play Integrity itself.
      confirmation = await signInWithPhoneNumber(auth, phoneE164);
    } catch (e) {
      // Never fail silently: surface a clear, translatable error to the screen.
      throw toSendOtpError(e);
    }
    return {
      phone: phoneE164,
      async confirm(code: string) {
        // Android may complete SMS Retriever auto-verification and sign the
        // Firebase user in before the farmer presses Verify. Redeeming the SMS
        // again then returns `auth/session-expired` because the one-time code
        // was already consumed by the native SDK. Accept only a current user
        // whose verified Firebase phone exactly matches this request.
        const autoVerifiedUser = auth.currentUser;
        if (autoVerifiedUser?.phoneNumber === phoneE164) {
          logger.info('firebaseAuth.confirmOtp', 'auto_verified_user_reused');
          return toCredential(autoVerifiedUser, 'phone');
        }
        let result;
        try {
          // RNFirebase's Android ConfirmationResult.confirm() delegates to a
          // process-global native verification ID. A resend or overlapping
          // callback can overwrite that global and make a brand-new SMS look
          // expired. Bind this code to the immutable verification ID returned
          // for this exact request instead.
          if (confirmation.verificationId) {
            const phoneCredential = PhoneAuthProvider.credential(
              confirmation.verificationId,
              code,
            );
            result = await signInWithCredential(auth, phoneCredential);
          } else {
            // Defensive compatibility for an unexpected SDK result without an
            // ID. The provider normally rejects this before reaching here.
            result = await confirmation.confirm(code);
          }
          // The native `confirm` resolves to `null` if no user comes back.
          if (!result?.user) {
            throw new AuthError('auth/invalid-code', 'auth.otpIncorrect');
          }
        } catch (e) {
          // The native SMS Retriever can finish auto-verification
          // asynchronously, in the small window between the pre-check above
          // and this manual redemption failing -- the OS may silently
          // consume the code between the two. Re-check auth.currentUser once
          // more before surfacing an error to the farmer: if the phone now
          // matches, the farmer really is signed in and this was a false
          // "code expired", not a real failure. Read-only phone-matched
          // check, not a retry of the confirm() call itself.
          const raceWinner = auth.currentUser;
          if (raceWinner?.phoneNumber === phoneE164) {
            logger.info(
              'firebaseAuth.confirmOtp',
              'auto_verified_user_reused_after_race',
            );
            return toCredential(raceWinner, 'phone');
          }
          throw toConfirmOtpError(e);
        }
        // Keep token retrieval outside the code-confirmation catch: a missing or
        // expired ID token must never be mislabeled as an accepted OTP.
        return toCredential(result.user, 'phone');
      },
    };
  },

  async signInWithGoogle(googleIdToken) {
    const credential = GoogleAuthProvider.credential(googleIdToken);
    const result = await signInWithCredential(getFirebaseAuth(), credential);
    return toCredential(result.user, 'google');
  },

  async signInWithApple({ identityToken, rawNonce }) {
    // Native AppleAuthProvider takes (idToken, rawNonce) positionally — unlike
    // the JS SDK's OAuthProvider('apple.com').credential({ idToken, rawNonce }).
    const credential = AppleAuthProvider.credential(identityToken, rawNonce);
    const result = await signInWithCredential(getFirebaseAuth(), credential);
    return toCredential(result.user, 'apple');
  },

  /**
   * Force-refresh the current Firebase id token. Firebase manages the refresh
   * token internally, so we ignore the passed value and read the live user.
   */
  async refreshToken(): Promise<RefreshedTokens | null> {
    const auth = getFirebaseAuth();
    const user = auth.currentUser;
    if (!user) return null;
    try {
      const result = await getIdTokenResult(user, true);
      return {
        idToken: result.token,
        // Same reason as toCredential() above — not exposed by the native SDK.
        refreshToken: '',
        expiresAt: new Date(result.expirationTime).getTime(),
      };
    } catch (e) {
      const code = (e as { code?: string } | null)?.code;
      const category = firebaseAuthErrorCategory(code);
      logger.warn('firebaseAuth.refresh', `error_category=${category}`);
      if (SESSION_INVALID_CODES.has(category)) {
        // The session really is gone — the caller should sign out.
        return null;
      }
      // A dropped connection, rate limit, or any other transient/unrecognized
      // failure is not proof the session is invalid. Throw distinctly so
      // authStore.refreshSession() keeps the current session and retries
      // later instead of signing the farmer out.
      throw new AuthError('auth/transient-refresh-failure', 'auth.otpNetworkError');
    }
  },

  async signOut() {
    await fbSignOut(getFirebaseAuth());
  },
};
