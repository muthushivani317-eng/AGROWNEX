import { AuthError } from './types';

/** Keep the visible field national-only while accepting a pasted +91 value. */
export function sanitizeIndianPhoneInput(value: string): string {
  const digits = value.replace(/\D/g, '');
  const national = digits.length > 10 && digits.startsWith('91') ? digits.slice(2) : digits;
  return national.slice(0, 10);
}

/** Normalize an Indian mobile number to the only accepted wire form. */
export function normalizeIndianPhone(value: string): string {
  const compact = value.trim().replace(/[\s()-]/g, '');
  const national = compact.startsWith('+91') ? compact.slice(3) : compact;
  if (!/^[6-9]\d{9}$/.test(national)) {
    throw new AuthError('auth/invalid-phone-number', 'auth.invalidPhone');
  }
  return `+91${national}`;
}
