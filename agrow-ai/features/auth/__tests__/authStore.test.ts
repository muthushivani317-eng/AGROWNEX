// Avoid pulling i18next side effects into the store unit test.
jest.mock('@/localization', () => ({
  setLanguage: jest.fn(() => Promise.resolve()),
  getLanguage: () => 'ta',
}));
jest.mock('@/services/apiClient', () => ({
  api: {
    post: jest.fn(() =>
      Promise.resolve({ user: { farmer_ref: 'farmer_test_1' }, profile: null }),
    ),
  },
  configureApiAuth: jest.fn(),
}));

// Replace the real (env-selected) provider with a controllable double so the
// refresh-failure tests below don't depend on which provider the current env
// happens to resolve to.
jest.mock('../services/authProvider', () => ({
  authProvider: {
    refreshToken: jest.fn(async (refreshToken: string) => ({
      idToken: `refreshed-${Math.random().toString(36).slice(2)}`,
      refreshToken,
      expiresAt: Date.now() + 3_600_000,
    })),
    signOut: jest.fn(async () => {}),
  },
}));

import { appStorage, initSecureStorage, secureStorage, StorageKeys } from '@/lib/storage';

import { authProvider } from '../services/authProvider';
import { useAuthStore } from '../store/authStore';
import { AuthError, type AuthCredential } from '../types';

const credential: AuthCredential = {
  uid: 'user_1',
  phone: '+919876543210',
  email: null,
  displayName: null,
  photoUrl: null,
  idToken: 'id-token',
  refreshToken: 'refresh-token',
  expiresAt: Date.now() + 3_600_000,
  provider: 'phone',
};

beforeAll(async () => {
  await initSecureStorage();
});

describe('authStore', () => {
  beforeEach(() => {
    secureStorage.remove(StorageKeys.authTokens);
    appStorage.remove(StorageKeys.authUser);
    appStorage.remove(StorageKeys.onboarded);
    appStorage.remove(StorageKeys.languageSelected);
    useAuthStore.setState({
      status: 'initializing',
      user: null,
      tokens: null,
      hasOnboarded: false,
      languageSelected: false,
    });
  });

  it('signIn creates an unfinished profile and persists the session', async () => {
    await useAuthStore.getState().signIn(credential, 'ta');

    const state = useAuthStore.getState();
    expect(state.status).toBe('authenticated');
    expect(state.user?.id).toBe('user_1');
    expect(state.user?.profileCompleted).toBe(false);
    expect(state.user?.role).toBe('farmer'); // RBAC default
    expect(state.tokens?.idToken).toBe('id-token');
    expect(secureStorage.getString(StorageKeys.authTokens)).toContain('id-token');
  });

  it('refreshSession(force) rotates the id token via the provider', async () => {
    await useAuthStore.getState().signIn(credential, 'ta');
    const before = useAuthStore.getState().tokens?.idToken;

    const token = await useAuthStore.getState().refreshSession({ force: true });
    expect(token).toBeTruthy();
    // Mock provider issues a fresh, different id token.
    expect(useAuthStore.getState().tokens?.idToken).not.toBe(before);
    expect(useAuthStore.getState().status).toBe('authenticated');
  });

  it('keeps the session when refresh fails transiently (e.g. a dropped connection), instead of signing out', async () => {
    await useAuthStore.getState().signIn(credential, 'ta');
    const before = useAuthStore.getState().tokens?.idToken;

    (authProvider.refreshToken as jest.Mock).mockRejectedValueOnce(
      new AuthError('auth/transient-refresh-failure', 'auth.otpNetworkError'),
    );

    const token = await useAuthStore.getState().refreshSession({ force: true });

    expect(token).toBe(before);
    expect(useAuthStore.getState().status).toBe('authenticated');
    expect(useAuthStore.getState().tokens?.idToken).toBe(before);
  });

  it('signs out when the provider reports the session is genuinely invalid', async () => {
    await useAuthStore.getState().signIn(credential, 'ta');

    (authProvider.refreshToken as jest.Mock).mockResolvedValueOnce(null);

    const token = await useAuthStore.getState().refreshSession({ force: true });

    expect(token).toBeNull();
    expect(useAuthStore.getState().status).toBe('unauthenticated');
  });

  it('updateUser marks the profile completed', async () => {
    await useAuthStore.getState().signIn(credential, 'ta');
    await useAuthStore.getState().updateUser({
      name: 'Muthu',
      district: 'madurai',
      profileCompleted: true,
    });

    expect(useAuthStore.getState().user?.profileCompleted).toBe(true);
    expect(useAuthStore.getState().user?.name).toBe('Muthu');
  });

  it('signOut clears session and storage', async () => {
    await useAuthStore.getState().signIn(credential, 'ta');
    await useAuthStore.getState().signOut();

    const state = useAuthStore.getState();
    expect(state.status).toBe('unauthenticated');
    expect(state.user).toBeNull();
    expect(state.tokens).toBeNull();
    expect(secureStorage.getString(StorageKeys.authTokens)).toBeNull();
  });

  it('bootstrap restores a persisted session', async () => {
    await useAuthStore.getState().signIn(credential, 'ta');
    useAuthStore.setState({ status: 'initializing', user: null, tokens: null });

    await useAuthStore.getState().bootstrap();
    expect(useAuthStore.getState().status).toBe('authenticated');
    expect(useAuthStore.getState().user?.id).toBe('user_1');
  });

  it('clears only corrupt startup session state and fails closed to signed out', async () => {
    secureStorage.set(StorageKeys.authTokens, '{not-json');
    appStorage.set(StorageKeys.authUser, '{not-json');
    appStorage.set(StorageKeys.onboarded, 'true');
    appStorage.set(StorageKeys.languageSelected, 'true');

    await useAuthStore.getState().bootstrap();

    expect(useAuthStore.getState()).toMatchObject({
      status: 'unauthenticated',
      hasOnboarded: true,
      languageSelected: true,
    });
    expect(secureStorage.getString(StorageKeys.authTokens)).toBeNull();
    expect(appStorage.getString(StorageKeys.authUser)).toBeNull();
  });
});
