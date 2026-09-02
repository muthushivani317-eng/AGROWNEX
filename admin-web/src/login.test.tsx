import { describe, expect, it, vi } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { Login, loginErrorMessage } from './Login';
vi.mock('./auth', () => ({ signInAdmin: vi.fn() }));
describe('Owner sign-in', () => {
  it('renders accessible fields and preserves password-manager support', () => {
    const html = renderToStaticMarkup(<Login onSuccess={() => {}}/>);
    expect(html).toContain('Welcome back');
    expect(html).toContain('autoComplete="username"');
    expect(html).toContain('autoComplete="current-password"');
    expect(html).toContain('type="password"');
    expect(html).toContain('aria-label="Show password"');
    expect(html).toContain('id="admin-recaptcha"');
    expect(html).toContain('MFA required');
  });
  it('does not offer invitation activation or longer-lived sessions', () => {
    const html = renderToStaticMarkup(<Login onSuccess={() => {}}/>);
    expect(html).not.toContain('Activate invitation');
    expect(html).not.toContain('Remember this device');
    expect(html).toContain('Public registration and invitations are disabled');
    expect(html).toContain('Sign in securely');
    expect(html).toContain('disabled=""');
  });
  it('does not reveal whether an email has an account', () => {
    expect(loginErrorMessage({ code: 'auth/user-not-found' })).toBe(loginErrorMessage({ code: 'auth/wrong-password' }));
    expect(loginErrorMessage({ code: 'auth/invalid-credential' })).toBe('Check your email and password, then try again.');
  });
  it('explains retryable and MFA failures', () => {
    expect(loginErrorMessage({ code: 'auth/too-many-requests' })).toContain('Wait');
    expect(loginErrorMessage({ code: 'auth/network-request-failed' })).toContain('connection');
    expect(loginErrorMessage({ code: 'auth/invalid-verification-code' })).toContain('verification code');
    expect(loginErrorMessage(new Error('Multi-factor verification was cancelled.'))).toContain('cancelled');
    expect(loginErrorMessage(null)).toContain('Sign-in could not be completed');
  });
});
