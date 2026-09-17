import { logger } from '@/lib/logger';

import { AuthError, type AuthCredential, type AuthProvider } from '../types';

const DEV_OTP = process.env.EXPO_PUBLIC_DEV_OTP ?? '';
const TOKEN_TTL_MS = 60 * 60 * 1000; // 1 hour, like a Firebase id token.
const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

function makeCredential(
  partial: Partial<AuthCredential> & Pick<AuthCredential, 'provider'>,
): AuthCredential {
  const uid = partial.uid ?? `mock_${Math.random().toString(36).slice(2, 10)}`;
  return {
    uid,
    phone: partial.phone ?? null,
    email: partial.email ?? null,
    displayName: partial.displayName ?? null,
    photoUrl: partial.photoUrl ?? null,
    idToken: `mock-id-token.${uid}.${Date.now()}`,
    refreshToken: `mock-refresh.${uid}`,
    expiresAt: Date.now() + TOKEN_TTL_MS,
    provider: partial.provider,
  };
}

/**
 * Local, network-free auth used until Firebase env vars are configured. Accepts
 * an explicitly configured development OTP. Swapped for `firebaseAuthProvider` automatically
 * once `EXPO_PUBLIC_FIREBASE_*` is present. Social methods ignore their token
 * inputs (there is no real IdP) and return a demo credential.
 */
export const mockAuthProvider: AuthProvider = {
  async sendOtp(phoneE164) {
    logger.info('mockAuth', 'event=otp_requested provider=development_mock');
    await wait(800);
    return {
      phone: phoneE164,
      async confirm(code: string) {
        await wait(700);
        if (code !== DEV_OTP) {
          throw new AuthError('auth/invalid-code', 'auth.otpIncorrect');
        }
        return makeCredential({ provider: 'phone', phone: phoneE164 });
      },
    };
  },

  async signInWithGoogle() {
    await wait(600);
    return makeCredential({
      provider: 'google',
      uid: 'mock_google_demo',
      email: 'demo.farmer@gmail.com',
      displayName: 'Demo Farmer',
    });
  },

  async signInWithApple() {
    await wait(600);
    return makeCredential({
      provider: 'apple',
      uid: 'mock_apple_demo',
      email: 'demo@icloud.com',
    });
  },

  /** Issue a fresh mock token for the same session (unlimited renewals). */
  async refreshToken(refreshToken) {
    await wait(150);
    const uid = refreshToken.replace('mock-refresh.', '') || 'mock_user';
    return {
      idToken: `mock-id-token.${uid}.${Date.now()}`,
      refreshToken,
      expiresAt: Date.now() + TOKEN_TTL_MS,
    };
  },

  async signOut() {
    logger.info('mockAuth', 'signOut');
    await wait(150);
  },
};
