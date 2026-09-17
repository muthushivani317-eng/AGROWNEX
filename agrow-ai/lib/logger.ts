import { isDev } from '@/config/env';

/**
 * Thin logging wrapper. In development it prints to the console; in production
 * it stays quiet for debug logs. This is also the single place that forwards
 * to Crashlytics, so every call site (including ErrorBoundary) gets crash
 * reporting for free. Never log secrets, tokens, or OTP values.
 */
type Level = 'debug' | 'info' | 'warn' | 'error';

const FIREBASE_AUTH_ERROR_CATEGORIES = new Set([
  'auth/invalid-phone-number',
  'auth/missing-phone-number',
  'auth/too-many-requests',
  'auth/quota-exceeded',
  'auth/billing-not-enabled',
  'auth/operation-not-allowed',
  'auth/network-request-failed',
  'auth/app-not-authorized',
  'auth/missing-client-identifier',
  'auth/invalid-app-credential',
  'auth/captcha-check-failed',
  'auth/invalid-recaptcha-token',
  'auth/invalid-verification-code',
  'auth/invalid-code',
  'auth/session-expired',
  'auth/code-expired',
  'auth/internal-error',
  'auth/user-token-expired',
  'auth/user-disabled',
  'auth/invalid-user-token',
  'auth/user-not-found',
  'auth/user-mismatch',
  'auth/invalid-user',
]);

/**
 * Forwards an error-level log to Crashlytics as a non-fatal error, with any
 * accompanying string args (e.g. a React componentStack) attached as a
 * breadcrumb first.
 *
 * Uses a lazy require (not a static import) and a try/catch around the whole
 * thing deliberately: the native Crashlytics module is absent in Expo Go, on
 * web, and in any dev client built before this was wired in, and a static
 * import would throw at module-evaluation time -- before any try/catch here
 * could catch it. Crash reporting must never be the thing that crashes the app.
 */
function reportToCrashlytics(scope: string, args: unknown[]) {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const crashlytics = require('@react-native-firebase/crashlytics').default;
    const instance = crashlytics();
    const error = args.find((a): a is Error => a instanceof Error);
    const context = args
      .filter((a) => a !== error)
      .map((a) => (typeof a === 'string' ? a : JSON.stringify(a)))
      .join(' ');
    if (context) void instance.log(`[${scope}] ${context}`);
    if (error) void instance.recordError(error, scope);
  } catch {
    // Native module unavailable -- no-op.
  }
}

/**
 * Record a Firebase Authentication failure without attaching request data.
 *
 * Only an explicit set of documented, non-sensitive Firebase error codes is
 * accepted. Everything else is collapsed to `unknown`.
 */
export function firebaseAuthErrorCategory(code: unknown, message?: unknown): string {
  if (typeof code === 'string' && FIREBASE_AUTH_ERROR_CATEGORIES.has(code)) {
    return code;
  }
  // Android Firebase Auth currently exposes reCAPTCHA Enterprise status 17202
  // as `auth/unknown`. Recognize only its fixed SDK sentence; never forward or
  // persist the raw native message because other failures may contain PII.
  if (
    typeof message === 'string'
    && message.toLowerCase().includes('request contains an invalid recaptcha token')
  ) {
    return 'auth/invalid-recaptcha-token';
  }
  return 'unknown';
}

export function reportFirebaseAuthErrorCategory(
  operation: 'sendOtp' | 'confirmOtp',
  code: unknown,
  message?: unknown,
): string {
  const category = firebaseAuthErrorCategory(code, message);
  reportToCrashlytics(
    `firebaseAuth.${operation}`,
    [new Error(`firebase_auth_category:${category}`)],
  );
  return category;
}

function log(level: Level, scope: string, ...args: unknown[]) {
  if (!isDev && level === 'debug') return;
  const tag = `[${scope}]`;
  // eslint-disable-next-line no-console
  (console[level] ?? console.log)(tag, ...args);
  if (level === 'error') reportToCrashlytics(scope, args);
}

export const logger = {
  debug: (scope: string, ...a: unknown[]) => log('debug', scope, ...a),
  info: (scope: string, ...a: unknown[]) => log('info', scope, ...a),
  warn: (scope: string, ...a: unknown[]) => log('warn', scope, ...a),
  error: (scope: string, ...a: unknown[]) => log('error', scope, ...a),
};
