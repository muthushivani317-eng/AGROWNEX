import type { TFunction } from 'i18next';

import { AuthError } from './types';
import { ApiError } from '@/types';

const AUTH_MESSAGE_KEYS = new Set([
  'auth.invalidPhone',
  'auth.otpQuotaExceeded',
  'auth.otpNetworkError',
  'auth.otpVerificationUnavailable',
  'auth.otpBillingRequired',
  'auth.otpPhoneSignInDisabled',
  'auth.otpSendFailed',
  'auth.otpIncorrect',
  'auth.otpCodeExpired',
  'auth.sessionExpired',
  'auth.otpConfirmFailed',
  'auth.signInFailed',
  'auth.serviceUnavailable',
]);

const ENGLISH_LAST_RESORT = {
  send: "Couldn't send the verification code. Please try again.",
  confirm: "Couldn't verify the code. Please try again.",
  signIn: "Couldn't complete sign in. Please try again.",
} as const;

/** Resolve only allowlisted auth keys and never return a raw dotted key. */
export function authErrorMessage(
  t: TFunction,
  error: unknown,
  operation: keyof typeof ENGLISH_LAST_RESORT,
): string {
  const fallbackKey = operation === 'send'
    ? 'auth.otpSendFailed'
    : operation === 'confirm'
      ? 'auth.otpConfirmFailed'
      : 'auth.signInFailed';
  const safeMessage = error instanceof AuthError
    ? error.message
    : typeof error === 'object' && error !== null && 'message' in error
      ? (error as { message?: unknown }).message
      : null;
  const candidate = typeof safeMessage === 'string' && AUTH_MESSAGE_KEYS.has(safeMessage)
    ? safeMessage
    : fallbackKey;
  const fallback = ENGLISH_LAST_RESORT[operation];
  const translated = t(candidate, { defaultValue: fallback });
  return !translated || translated === candidate || /^[a-z]+(?:\.[\w-]+)+$/i.test(translated)
    ? fallback
    : translated;
}

/** Reduce backend exchange failures to non-sensitive operational categories. */
export function backendAuthFailure(error: unknown): {
  category: string;
  messageKey: 'auth.serviceUnavailable' | 'auth.signInFailed';
} {
  if (!(error instanceof ApiError)) {
    return { category: 'backend_verify_failed', messageKey: 'auth.signInFailed' };
  }
  const status = Number.isInteger(error.status) ? error.status : 0;
  const safeCode = /^[a-z0-9_-]+$/i.test(error.errorCode) ? error.errorCode : 'unknown';
  return {
    category: `backend_http_${status}_${safeCode}`,
    messageKey: status === 0 || status >= 500
      ? 'auth.serviceUnavailable'
      : 'auth.signInFailed',
  };
}
