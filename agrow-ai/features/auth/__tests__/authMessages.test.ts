import { authErrorMessage, backendAuthFailure } from '../authMessages';
import { AuthError } from '../types';
import { ApiError } from '@/types';

describe('authErrorMessage', () => {
  const translations: Record<string, string> = {
    'auth.invalidPhone': 'Invalid phone number',
    'auth.otpSendFailed': "Couldn't send the verification code. Please try again.",
    'auth.otpConfirmFailed': "Couldn't verify the code. Please try again.",
    'auth.otpCodeExpired': 'This verification code has expired. Request a new code.',
    'auth.signInFailed': "Couldn't complete sign in. Please try again.",
    'auth.serviceUnavailable': 'The authentication service is temporarily unavailable. Please try again later.',
    'auth.otpBillingRequired': 'SMS sign-in needs Firebase billing to be enabled. Please contact AgrowAI support.',
    'auth.otpPhoneSignInDisabled': 'Phone sign-in is disabled for this app. Please contact AgrowAI support.',
  };
  const t = ((key: string, options?: { defaultValue?: string }) =>
    translations[key] ?? options?.defaultValue ?? key) as any;

  it('maps an allowlisted Firebase error to localized text', () => {
    expect(authErrorMessage(t, new AuthError('auth/invalid-phone-number', 'auth.invalidPhone'), 'send'))
      .toBe('Invalid phone number');
  });

  it.each([
    ['auth/billing-not-enabled', 'auth.otpBillingRequired', 'SMS sign-in needs Firebase billing to be enabled. Please contact AgrowAI support.'],
    ['auth/operation-not-allowed', 'auth.otpPhoneSignInDisabled', 'Phone sign-in is disabled for this app. Please contact AgrowAI support.'],
  ])('keeps the actionable message for %s', (code, messageKey, expected) => {
    expect(authErrorMessage(t, new AuthError(code, messageKey), 'send')).toBe(expected);
  });

  it('keeps an allowlisted expired-code message after query-state serialization', () => {
    expect(authErrorMessage(t, {
      code: 'auth/session-expired',
      message: 'auth.otpCodeExpired',
    }, 'confirm')).toBe('This verification code has expired. Request a new code.');
  });

  it('maps a backend 500 to a sanitized temporary-service category', () => {
    const result = backendAuthFailure(new ApiError({
      status: 500,
      errorCode: 'internal_error',
      message: 'server detail must not be surfaced',
    }));
    expect(result).toEqual({
      category: 'backend_http_500_internal_error',
      messageKey: 'auth.serviceUnavailable',
    });
    expect(JSON.stringify(result)).not.toContain('server detail');
  });

  it('uses a safe fallback and never leaks an unknown dotted key', () => {
    const message = authErrorMessage(t, new AuthError('auth/internal-error', 'auth.somethingWrong'), 'send');
    expect(message).toBe("Couldn't send the verification code. Please try again.");
    expect(message).not.toContain('auth.');
  });

  it('uses a safe confirmation fallback for unknown native failures', () => {
    expect(authErrorMessage(t, new Error('native'), 'confirm'))
      .toBe("Couldn't verify the code. Please try again.");
  });

  it('uses a safe sign-in fallback for unknown errors', () => {
    expect(authErrorMessage(t, new AuthError('auth/internal', 'auth.untranslated'), 'signIn'))
      .toBe("Couldn't complete sign in. Please try again.");
  });
});
