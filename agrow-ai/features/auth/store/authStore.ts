import { create } from 'zustand';

import { env, isAllowlisted, isAllowlistConfigured } from '@/config/env';
import { setLanguage } from '@/localization';
import { logger } from '@/lib/logger';
import { appStorage, initSecureStorage, secureStorage, StorageKeys } from '@/lib/storage';
import { api, configureApiAuth } from '@/services/apiClient';
import type { SupportedLanguage } from '@/types';

import { authProvider } from '../services/authProvider';
import { AuthError } from '../types';
import type { AuthCredential, AuthTokens, AuthUser } from '../types';
import { backendAuthFailure } from '../authMessages';

export type AuthStatus = 'initializing' | 'unauthenticated' | 'authenticated';

/**
 * Farmer profile row returned by `/auth/otp/verify` (see
 * backend/app/modules/auth/schemas.py → ProfileOut). Non-null only when this
 * farmer already completed profile setup on a previous sign-in.
 */
interface BackendFarmerProfile {
  full_name: string | null;
  language: string;
  district: string | null;
  block: string | null;
  village: string | null;
  profile_photo: string | null;
  experience_years: number | null;
  primary_crop: string | null;
  secondary_crop: string | null;
}

interface OtpVerifyResponse {
  user: { farmer_ref: string };
  profile: BackendFarmerProfile | null;
}

interface AuthState {
  status: AuthStatus;
  user: AuthUser | null;
  tokens: AuthTokens | null;
  hasOnboarded: boolean;
  languageSelected: boolean;
  /** Epoch millis of the last recorded user activity (for idle timeout). */
  lastActiveAt: number;

  bootstrap: () => Promise<void>;
  signIn: (credential: AuthCredential, language: SupportedLanguage) => Promise<void>;
  updateUser: (patch: Partial<AuthUser>) => Promise<void>;
  completeOnboarding: () => Promise<void>;
  confirmLanguageSelection: () => void;
  resetStartupState: () => Promise<void>;
  /** Refresh the id token if it is expired/near expiry. Returns the valid token. */
  refreshSession: (opts?: { force?: boolean }) => Promise<string | null>;
  /** Record activity to reset the idle-timeout window. */
  touchActivity: () => void;
  signOut: () => Promise<void>;
}

function credentialToUser(cred: AuthCredential, language: SupportedLanguage): AuthUser {
  return {
    id: cred.uid,
    farmerRef: null,
    phone: cred.phone,
    email: cred.email,
    name: cred.displayName,
    photoUrl: cred.photoUrl,
    language,
    district: null,
    block: null,
    village: null,
    experienceYears: null,
    gender: null,
    education: null,
    preferredCrops: [],
    role: 'farmer',
    profileCompleted: false,
    createdAt: new Date().toISOString(),
  };
}

/** True when the session has been idle past the configured timeout. */
function isIdleExpired(lastActiveAt: number): boolean {
  return Date.now() - lastActiveAt > env.sessionIdleTimeoutMs;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  status: 'initializing',
  user: null,
  tokens: null,
  hasOnboarded: false,
  languageSelected: false,
  lastActiveAt: Date.now(),

  async bootstrap() {
    try {
      await initSecureStorage();
      const rawTokens = secureStorage.getString(StorageKeys.authTokens);
      const rawUser = appStorage.getString(StorageKeys.authUser);
      const tokens = secureStorage.getJSON<AuthTokens>(StorageKeys.authTokens);
      const user = appStorage.getJSON<AuthUser>(StorageKeys.authUser);
      const rawOnboarded = appStorage.getString(StorageKeys.onboarded);
      const rawLanguageSelected = appStorage.getString(StorageKeys.languageSelected);
      const hasOnboarded = rawOnboarded === 'true';
      const languageSelected = rawLanguageSelected === 'true';
      const lastActiveAt =
        Number(appStorage.getString(StorageKeys.lastActiveAt)) || Date.now();

      const corruptSession =
        Boolean(rawTokens && !tokens) ||
        Boolean(rawUser && !user) ||
        Boolean(tokens) !== Boolean(user);
      if (corruptSession) {
        logger.warn('authStore.bootstrap', 'invalid_persisted_session_reset');
        secureStorage.remove(StorageKeys.authTokens);
        appStorage.remove(StorageKeys.authUser);
        appStorage.remove(StorageKeys.lastActiveAt);
      }
      if (rawOnboarded !== null && rawOnboarded !== 'true' && rawOnboarded !== 'false') {
        logger.warn('authStore.bootstrap', 'invalid_onboarding_state_reset');
        appStorage.remove(StorageKeys.onboarded);
      }
      if (
        rawLanguageSelected !== null &&
        rawLanguageSelected !== 'true' &&
        rawLanguageSelected !== 'false'
      ) {
        logger.warn('authStore.bootstrap', 'invalid_language_state_reset');
        appStorage.remove(StorageKeys.languageSelected);
      }

      if (!corruptSession && tokens && user) {
        // Enforce the inactivity timeout across cold starts (docs/SECURITY.md).
        if (isIdleExpired(lastActiveAt)) {
          logger.info('authStore', 'session idle-expired — signing out');
          await get().signOut();
          set({ hasOnboarded, languageSelected });
          return;
        }
        if (user.language) await setLanguage(user.language);
        set({ status: 'authenticated', tokens, user, hasOnboarded, languageSelected, lastActiveAt });
        // Renew the token if it expired while the app was closed (auto-login).
        void get().refreshSession();
      } else {
        set({ status: 'unauthenticated', hasOnboarded, languageSelected });
      }
    } catch {
      logger.error('authStore.bootstrap', 'auth_restoration_failed');
      set({ status: 'unauthenticated' });
      throw new Error('auth_restoration_failed');
    }
  },

  async signIn(credential, language) {
    const user = credentialToUser(credential, language);

    // Ensure the backend has a user row for this Firebase identity before we
    // finalise a local session. The endpoint creates/finds a user keyed by
    // firebase_uid; without it, every subsequent API call 404s user_not_found.
    // Its response also carries this farmer's saved profile, if one exists —
    // previously discarded here, which meant profileCompleted was always
    // reset to false on a fresh sign-in and every already-registered farmer
    // (reinstall, new device, session expiry) got routed back through
    // "complete your profile" instead of straight to the home tabs.
    let backendProfile: BackendFarmerProfile | null = null;
    try {
      const result = await api.post<OtpVerifyResponse>('/auth/otp/verify', {
        id_token: credential.idToken,
      });
      backendProfile = result.profile;
      user.farmerRef = result.user.farmer_ref;
    } catch (e) {
      const failure = backendAuthFailure(e);
      logger.error('authStore.signIn', `error_category=${failure.category}`);
      throw new AuthError('auth/backend-verify-failed', failure.messageKey);
    }

    if (backendProfile) {
      user.profileCompleted = true;
      user.name = backendProfile.full_name ?? user.name;
      user.district = backendProfile.district;
      user.block = backendProfile.block;
      user.village = backendProfile.village;
      user.experienceYears = backendProfile.experience_years;
      user.photoUrl = backendProfile.profile_photo ?? user.photoUrl;
      user.preferredCrops = [backendProfile.primary_crop, backendProfile.secondary_crop].filter(
        (crop): crop is string => Boolean(crop),
      );
    }

    // App-level access lock. Even once real Firebase auth is wired up, only
    // pre-approved identities may complete sign-in. This runs on EVERY provider
    // (phone OTP / Google / Apple / mock) because they all finalise the session
    // here — there is no other path into an authenticated state.
    if (isAllowlistConfigured) {
      const permitted = isAllowlisted(user.phone) || isAllowlisted(user.email);
      if (!permitted) {
        logger.warn('authStore', 'sign-in blocked — identity not in admin allowlist');
        // Revoke the provider session just established and drop any partial
        // local session, then surface a clear error instead of letting them in.
        await authProvider.signOut().catch(() => {});
        await get().signOut();
        throw new AuthError('auth/not-authorized', 'auth.notAuthorized');
      }
    } else {
      // Requirement: never lock out a fresh dev clone that has no allowlist set.
      logger.warn(
        'authStore',
        'EXPO_PUBLIC_ADMIN_ALLOWLIST not configured — sign-in is unrestricted',
      );
    }

    const tokens: AuthTokens = {
      idToken: credential.idToken,
      refreshToken: credential.refreshToken,
      expiresAt: credential.expiresAt,
    };
    const now = Date.now();
    secureStorage.setJSON(StorageKeys.authTokens, tokens);
    appStorage.setJSON(StorageKeys.authUser, user);
    appStorage.set(StorageKeys.lastActiveAt, String(now));
    set({ status: 'authenticated', tokens, user, lastActiveAt: now });
  },

  async updateUser(patch) {
    const current = get().user;
    if (!current) return;
    const next: AuthUser = { ...current, ...patch };
    appStorage.setJSON(StorageKeys.authUser, next);
    if (patch.language && patch.language !== current.language) {
      await setLanguage(patch.language);
    }
    set({ user: next });
  },

  async completeOnboarding() {
    appStorage.set(StorageKeys.onboarded, 'true');
    set({ hasOnboarded: true });
  },

  confirmLanguageSelection() {
    appStorage.set(StorageKeys.languageSelected, 'true');
    set({ languageSelected: true });
  },

  async resetStartupState() {
    secureStorage.remove(StorageKeys.authTokens);
    appStorage.remove(StorageKeys.authUser);
    appStorage.remove(StorageKeys.lastActiveAt);
    appStorage.remove(StorageKeys.onboarded);
    appStorage.remove(StorageKeys.languageSelected);
    set({
      status: 'unauthenticated',
      tokens: null,
      user: null,
      hasOnboarded: false,
      languageSelected: false,
    });
  },

  async refreshSession(opts) {
    const { tokens, status } = get();
    if (status !== 'authenticated' || !tokens) return null;

    const needsRefresh =
      opts?.force || Date.now() >= tokens.expiresAt - env.tokenRefreshLeadMs;
    if (!needsRefresh) return tokens.idToken;

    try {
      const refreshed = await authProvider.refreshToken(tokens.refreshToken);
      if (!refreshed) {
        logger.info('authStore', 'refresh returned null — session invalid, signing out');
        await get().signOut();
        return null;
      }
      const next: AuthTokens = {
        idToken: refreshed.idToken,
        refreshToken: refreshed.refreshToken,
        expiresAt: refreshed.expiresAt,
      };
      secureStorage.setJSON(StorageKeys.authTokens, next);
      set({ tokens: next });
      return next.idToken;
    } catch (e) {
      if (e instanceof AuthError && e.code === 'auth/transient-refresh-failure') {
        // A dropped connection during refresh must never sign a farmer out of
        // a session that's still actually valid — keep the current token and
        // retry on the next refresh cycle instead (see farmer-release-
        // readiness audit, 2026-08-18).
        logger.info('authStore.refreshSession', 'transient refresh failure — keeping session');
        return tokens.idToken;
      }
      logger.warn('authStore.refreshSession', e);
      return null;
    }
  },

  touchActivity() {
    const now = Date.now();
    appStorage.set(StorageKeys.lastActiveAt, String(now));
    set({ lastActiveAt: now });
  },

  async signOut() {
    secureStorage.remove(StorageKeys.authTokens);
    appStorage.remove(StorageKeys.authUser);
    appStorage.remove(StorageKeys.lastActiveAt);
    set({ status: 'unauthenticated', tokens: null, user: null });
  },
}));

// Wire the HTTP client to the session without creating an import cycle
// (apiClient never imports the store).
configureApiAuth({
  getToken: () => useAuthStore.getState().tokens?.idToken ?? null,
  refreshSession: () => useAuthStore.getState().refreshSession({ force: true }),
  onUnauthorized: () => {
    void useAuthStore.getState().signOut();
  },
});
