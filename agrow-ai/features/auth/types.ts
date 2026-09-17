import type { SupportedLanguage } from '@/types';

/** Coarse role for Role-Based Access preparation (docs/SECURITY.md → RBAC). */
export type UserRole = 'farmer' | 'fpo' | 'officer' | 'admin';

/** App-level user profile (superset of the identity provider's user). */
export interface AuthUser {
  id: string;
  /**
   * Stable, farmer-facing reference code (e.g. "AGF-000123456"), from
   * backend/app/modules/auth/models.py → User.farmer_ref. This is what a
   * farmer gives an FPO/organization so it can request read access to their
   * data — see features/partnerLinks.
   */
  farmerRef: string | null;
  phone: string | null;
  name: string | null;
  email: string | null;
  photoUrl: string | null;
  language: SupportedLanguage;
  district: string | null;
  block: string | null;
  village: string | null;
  experienceYears: number | null;
  gender: string | null;
  education: string | null;
  preferredCrops: string[];
  role: UserRole;
  profileCompleted: boolean;
  createdAt: string;
}

export interface AuthTokens {
  idToken: string;
  refreshToken: string;
  /** Epoch millis when the id token expires. */
  expiresAt: number;
}

/** Fresh token set returned by a token refresh. */
export interface RefreshedTokens {
  idToken: string;
  refreshToken: string;
  expiresAt: number;
}

/** Raw credential returned by an identity provider on successful sign-in. */
export interface AuthCredential {
  uid: string;
  phone: string | null;
  email: string | null;
  displayName: string | null;
  photoUrl: string | null;
  idToken: string;
  refreshToken: string;
  expiresAt: number;
  provider: 'phone' | 'google' | 'apple';
}

/** Handle returned after an OTP is dispatched; confirms the entered code. */
export interface OtpConfirmation {
  phone: string;
  confirm: (code: string) => Promise<AuthCredential>;
}

/** Apple identity payload exchanged for a session credential. */
export interface AppleCredentialInput {
  identityToken: string;
  rawNonce: string;
  email: string | null;
  fullName: string | null;
}

/**
 * Identity provider contract. Implemented by both the real Firebase provider and
 * a local mock, selected at runtime — screens/hooks depend only on this
 * interface. Social methods take the OIDC token obtained from the platform flow
 * and exchange it for an app session credential.
 */
export interface AuthProvider {
  sendOtp: (phoneE164: string) => Promise<OtpConfirmation>;
  signInWithGoogle: (googleIdToken: string) => Promise<AuthCredential>;
  signInWithApple: (input: AppleCredentialInput) => Promise<AuthCredential>;
  /** Obtain a fresh id token, or null if the session can no longer be renewed. */
  refreshToken: (refreshToken: string) => Promise<RefreshedTokens | null>;
  signOut: () => Promise<void>;
}

export class AuthError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = 'AuthError';
  }
}
