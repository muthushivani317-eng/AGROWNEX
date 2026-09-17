import { mockAuthProvider } from '../services/mockAuthProvider';
import { AuthError } from '../types';

describe('mockAuthProvider', () => {
  it('issues a confirmation and accepts the dev OTP', async () => {
    const confirmation = await mockAuthProvider.sendOtp('+919876543210');
    expect(confirmation.phone).toBe('+919876543210');

    const credential = await confirmation.confirm('123456');
    expect(credential.provider).toBe('phone');
    expect(credential.phone).toBe('+919876543210');
    expect(credential.idToken).toContain('mock-id-token');
    expect(credential.expiresAt).toBeGreaterThan(Date.now());
  });

  it('rejects an incorrect OTP with an AuthError', async () => {
    const confirmation = await mockAuthProvider.sendOtp('+919876543210');
    await expect(confirmation.confirm('000000')).rejects.toBeInstanceOf(AuthError);
  });

  it('returns a google credential', async () => {
    const cred = await mockAuthProvider.signInWithGoogle('dev-mock');
    expect(cred.provider).toBe('google');
    expect(cred.email).toBeTruthy();
  });

  it('returns an apple credential', async () => {
    const cred = await mockAuthProvider.signInWithApple({
      identityToken: 'dev-mock',
      rawNonce: '',
      email: null,
      fullName: null,
    });
    expect(cred.provider).toBe('apple');
  });

  it('refreshes to a new id token for the same session', async () => {
    const cred = await mockAuthProvider.signInWithGoogle('dev-mock');
    const refreshed = await mockAuthProvider.refreshToken(cred.refreshToken);
    expect(refreshed).not.toBeNull();
    expect(refreshed?.expiresAt).toBeGreaterThan(Date.now());
    expect(refreshed?.refreshToken).toBe(cred.refreshToken);
  });
});
