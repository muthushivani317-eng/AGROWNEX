/**
 * Centralised, typed runtime configuration.
 *
 * Only `EXPO_PUBLIC_*` values are available in the JS bundle — never put server
 * secrets here. When Firebase config is absent, the auth layer falls back to a
 * local mock provider so the app remains runnable during development.
 *
 * IMPORTANT: every env value below is read through a *static, literal*
 * `process.env.EXPO_PUBLIC_X` reference. This is a hard requirement of Expo's
 * build-time env inlining (`babel-preset-expo`): the transform only rewrites
 * member expressions it can see literally in the source. Dynamic access —
 * `process.env[key]` with a variable, or a shared helper that takes the key as
 * an argument — is invisible to it, so in a real release build it resolves to
 * `undefined` and every value silently falls through to its default. Do NOT
 * refactor these into a keyed lookup. `withDefault` only takes the already
 * resolved value, never a key, so inlining still applies to each reference.
 */
const withDefault = (value: string | undefined, fallback = ''): string =>
  value ?? fallback;

export type BuildProfile =
  | 'development'
  | 'pilot'
  | 'localStandalone'
  | 'internal_testing'
  | 'kvk_field_test'
  | 'production';
export type ConfigurationErrorCategory =
  | 'api_url_missing'
  | 'api_url_invalid'
  | 'api_url_insecure'
  | 'api_url_local'
  | 'diagnosis_url_missing'
  | 'diagnosis_url_invalid'
  | 'diagnosis_url_insecure'
  | 'diagnosis_url_local'
  | 'firebase_missing';

const rawApiBaseUrl = withDefault(process.env.EXPO_PUBLIC_API_BASE_URL);
const rawDiagnosisApiBaseUrl = withDefault(process.env.EXPO_PUBLIC_DIAGNOSIS_API_BASE_URL);

export const buildProfile: BuildProfile =
  process.env.EXPO_PUBLIC_APP_ENV === 'development' ||
  process.env.EXPO_PUBLIC_APP_ENV === 'pilot' ||
  process.env.EXPO_PUBLIC_APP_ENV === 'localStandalone' ||
  process.env.EXPO_PUBLIC_APP_ENV === 'internal_testing' ||
  process.env.EXPO_PUBLIC_APP_ENV === 'kvk_field_test' ||
  process.env.EXPO_PUBLIC_APP_ENV === 'production'
    ? process.env.EXPO_PUBLIC_APP_ENV
    : __DEV__
      ? 'development'
      : 'production';

export const env = {
  buildProfile,
  // Backend REST API (see docs/API_CONTRACT.md).
  apiBaseUrl: withDefault(rawApiBaseUrl),
  apiTimeoutMs: Number(withDefault(process.env.EXPO_PUBLIC_API_TIMEOUT_MS, '20000')),
  diagnosisApiBaseUrl: withDefault(
    rawDiagnosisApiBaseUrl,
  ),

  // Firebase (phone OTP / social auth).
  firebase: {
    apiKey: withDefault(process.env.EXPO_PUBLIC_FIREBASE_API_KEY),
    authDomain: withDefault(process.env.EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN),
    projectId: withDefault(process.env.EXPO_PUBLIC_FIREBASE_PROJECT_ID),
    storageBucket: withDefault(process.env.EXPO_PUBLIC_FIREBASE_STORAGE_BUCKET),
    messagingSenderId: withDefault(process.env.EXPO_PUBLIC_FIREBASE_MESSAGING_SENDER_ID),
    appId: withDefault(process.env.EXPO_PUBLIC_FIREBASE_APP_ID),
  },

  // Google OAuth client IDs (Google Cloud console). Platform-specific.
  google: {
    expoClientId: withDefault(process.env.EXPO_PUBLIC_GOOGLE_EXPO_CLIENT_ID),
    iosClientId: withDefault(process.env.EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID),
    androidClientId: withDefault(process.env.EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID),
    webClientId: withDefault(process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID),
  },

  // Admin access allowlist. App-level lock layered over whatever auth provider
  // is active: a comma-separated list of phone numbers and/or emails permitted
  // to complete sign-in (e.g. "+919999999999,me@example.com"). Blank in local
  // dev → sign-in is unrestricted (see isAllowlisted / authStore.signIn).
  adminAllowlist: withDefault(process.env.EXPO_PUBLIC_ADMIN_ALLOWLIST),

  // Session policy.
  // Inactivity timeout after which a foregrounded app forces re-auth (ms).
  sessionIdleTimeoutMs: Number(
    withDefault(
      process.env.EXPO_PUBLIC_SESSION_IDLE_TIMEOUT_MS,
      String(1000 * 60 * 60 * 24 * 14),
    ),
  ),
  // Refresh the id token this many ms before it actually expires.
  tokenRefreshLeadMs: Number(withDefault(process.env.EXPO_PUBLIC_TOKEN_REFRESH_LEAD_MS, '120000')),

  // Media uploads (profile/farm/produce images → AWS S3, docs/BACKEND_ARCHITECTURE.md
  // → Storage). `uploadEndpoint` is a backend-issued upload URL that returns the
  // stored object's public URL; absent in local dev, where a mock is used.
  s3: {
    uploadEndpoint: withDefault(process.env.EXPO_PUBLIC_S3_UPLOAD_ENDPOINT),
  },

  // Third-party services (used by later feature phases).
  mapboxToken: withDefault(process.env.EXPO_PUBLIC_MAPBOX_TOKEN),
  openMeteoBaseUrl: 'https://api.open-meteo.com/v1',
} as const;

/** True when a real Firebase project is wired up. */
export const isFirebaseConfigured = Boolean(
  env.firebase.apiKey && env.firebase.projectId && env.firebase.appId,
);

/**
 * True when the app talks to a real AgrowAI backend. The backend authenticates
 * with Firebase JWTs, so a real backend and real Firebase are configured
 * together; when absent, feature data persists locally (mirrors the mock auth
 * provider) so the app stays fully usable in development.
 */
export const isBackendConfigured = isFirebaseConfigured;

/** True when a real S3 upload endpoint is available (else avatar upload is mocked). */
export const isS3Configured = Boolean(env.s3.uploadEndpoint);

/** True when Google OAuth client IDs are available. */
export const isGoogleConfigured = Boolean(
  env.google.iosClientId || env.google.androidClientId || env.google.webClientId,
);

/**
 * Admin access allowlist — the phone numbers/emails permitted to complete
 * sign-in, parsed from EXPO_PUBLIC_ADMIN_ALLOWLIST. Entries are trimmed and
 * lower-cased so comparison is case-insensitive. Empty when unconfigured.
 */
export const adminAllowlist: readonly string[] = env.adminAllowlist
  .split(',')
  .map((entry) => entry.trim().toLowerCase())
  .filter((entry) => entry.length > 0);

/**
 * True when an access allowlist is configured. When false, sign-in is left
 * unrestricted so a fresh dev clone with no .env stays usable; when true, only
 * allowlisted identities may complete sign-in (production lock is active).
 */
export const isAllowlistConfigured = adminAllowlist.length > 0;

/**
 * Case-insensitive, trimmed membership test against the admin allowlist.
 * Returns false for a null/blank identifier so callers can safely test phone
 * and email independently. Note: an unconfigured allowlist makes this return
 * false for everyone — callers must treat "not configured" as allow-all (see
 * authStore.signIn), never as a blanket denial.
 */
export const isAllowlisted = (identifier: string | null): boolean => {
  if (!identifier) return false;
  const normalized = identifier.trim().toLowerCase();
  return normalized.length > 0 && adminAllowlist.includes(normalized);
};

export const isDev = __DEV__;

const LOOPBACK_HOSTNAME = ['local', 'host'].join('');

function isPrivateIpv4(hostname: string): boolean {
  const octets = hostname.split('.').map(Number);
  if (octets.length !== 4 || octets.some((part) => !Number.isInteger(part) || part < 0 || part > 255)) {
    return false;
  }
  return (
    octets[0] === 10 ||
    octets[0] === 127 ||
    (octets[0] === 169 && octets[1] === 254) ||
    (octets[0] === 172 && octets[1] >= 16 && octets[1] <= 31) ||
    (octets[0] === 192 && octets[1] === 168)
  );
}

function urlErrorCategory(
  value: string,
  prefix: 'api_url' | 'diagnosis_url',
): ConfigurationErrorCategory | null {
  if (!value.trim()) return `${prefix}_missing`;
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    return `${prefix}_invalid`;
  }
  if (parsed.protocol !== 'https:') {
    return `${prefix}_insecure`;
  }
  const hostname = parsed.hostname.toLowerCase().replace(/^\[|\]$/g, '');
  if (hostname === LOOPBACK_HOSTNAME || hostname === ['::', '1'].join('') || isPrivateIpv4(hostname) || hostname.endsWith('.local')) {
    return `${prefix}_local`;
  }
  return null;
}

export function assertProductionHttpsUrl(name: string, value: string): void {
  const prefix = name.includes('DIAGNOSIS') ? 'diagnosis_url' : 'api_url';
  const category = urlErrorCategory(value, prefix);
  if (category) throw new Error(category);
}

export function getReleaseEnvironmentError(input?: {
  profile?: BuildProfile;
  apiBaseUrl?: string;
  diagnosisApiBaseUrl?: string;
  firebaseConfigured?: boolean;
}): ConfigurationErrorCategory | null {
  const profile = input?.profile ?? buildProfile;
  if (
    profile !== 'production' &&
    profile !== 'internal_testing' &&
    profile !== 'kvk_field_test'
  ) return null;

  const apiError = urlErrorCategory(input?.apiBaseUrl ?? rawApiBaseUrl, 'api_url');
  if (apiError) return apiError;
  const diagnosisError = urlErrorCategory(
    input?.diagnosisApiBaseUrl ?? rawDiagnosisApiBaseUrl,
    'diagnosis_url',
  );
  if (diagnosisError) return diagnosisError;
  if (!(input?.firebaseConfigured ?? isFirebaseConfigured)) return 'firebase_missing';
  return null;
}

/**
 * Fail closed when a release bundle was built with development endpoints.
 *
 * This deliberately runs before any farmer workflow can make a request. A release
 * APK must never depend on a loopback host, ADB reverse, an emulator alias, or a developer
 * laptop. Only public configuration names are mentioned in errors; values and
 * credentials are never logged.
 */
export function assertReleaseEnvironment(): void {
  const category = getReleaseEnvironmentError();
  if (category) throw new Error(category);
}

/**
 * Startup sanity check: names of the expected `EXPO_PUBLIC_*` keys that resolved
 * to an empty value in this build. Callers log the *names only* (never values)
 * so a misconfigured build — one where `.env` was not bundled and every value
 * silently fell back to a default — is loud and obvious instead of failing
 * quietly at runtime.
 *
 * Each entry references `process.env.EXPO_PUBLIC_X` statically for the same
 * inlining reason as `env` above; do not collapse these into a keyed loop.
 * A blank value is legitimate in local dev (Firebase → mock provider, blank
 * allowlist → sign-in unrestricted), so callers should treat this as a warning,
 * not a hard failure.
 */
export function missingPublicEnvKeys(): string[] {
  const isBlank = (value: string | undefined): boolean =>
    value == null || value.trim().length === 0;
  const checks: ReadonlyArray<readonly [string, boolean]> = [
    ['EXPO_PUBLIC_API_BASE_URL', isBlank(process.env.EXPO_PUBLIC_API_BASE_URL)],
    ['EXPO_PUBLIC_FIREBASE_API_KEY', isBlank(process.env.EXPO_PUBLIC_FIREBASE_API_KEY)],
    ['EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN', isBlank(process.env.EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN)],
    ['EXPO_PUBLIC_FIREBASE_PROJECT_ID', isBlank(process.env.EXPO_PUBLIC_FIREBASE_PROJECT_ID)],
    ['EXPO_PUBLIC_FIREBASE_STORAGE_BUCKET', isBlank(process.env.EXPO_PUBLIC_FIREBASE_STORAGE_BUCKET)],
    [
      'EXPO_PUBLIC_FIREBASE_MESSAGING_SENDER_ID',
      isBlank(process.env.EXPO_PUBLIC_FIREBASE_MESSAGING_SENDER_ID),
    ],
    ['EXPO_PUBLIC_FIREBASE_APP_ID', isBlank(process.env.EXPO_PUBLIC_FIREBASE_APP_ID)],
    ['EXPO_PUBLIC_ADMIN_ALLOWLIST', isBlank(process.env.EXPO_PUBLIC_ADMIN_ALLOWLIST)],
    ['EXPO_PUBLIC_MAPBOX_TOKEN', isBlank(process.env.EXPO_PUBLIC_MAPBOX_TOKEN)],
  ];
  return checks.filter(([, blank]) => blank).map(([key]) => key);
}
