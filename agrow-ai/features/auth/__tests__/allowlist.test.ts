// Avoid pulling i18next side effects into the store unit test.
jest.mock('@/localization', () => ({
  setLanguage: jest.fn(() => Promise.resolve()),
  getLanguage: () => 'ta',
}));

// Control the access allowlist per-test. The store reads these as live property
// accesses on the (shared) config module object, so mutating them here — plain
// data properties, no getters — drives each case at signIn() call time.
jest.mock('@/config/env', () => ({
  __esModule: true,
  ...jest.requireActual('@/config/env'),
  isAllowlistConfigured: false,
  isAllowlisted: jest.fn((_id: string | null) => false),
}));

import * as configEnv from '@/config/env';
import { initSecureStorage, secureStorage, StorageKeys } from '@/lib/storage';

import { useAuthStore } from '../store/authStore';
import { AuthError, type AuthCredential } from '../types';

const mockEnv = configEnv as unknown as {
  isAllowlistConfigured: boolean;
  isAllowlisted: jest.Mock<boolean, [string | null]>;
};

const baseCredential: AuthCredential = {
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

beforeEach(() => {
  mockEnv.isAllowlistConfigured = false;
  mockEnv.isAllowlisted.mockReset().mockReturnValue(false);
  secureStorage.remove(StorageKeys.authTokens);
  useAuthStore.setState({ status: 'initializing', user: null, tokens: null });
});

describe('authStore.signIn access lock', () => {
  it('rejects an identity that is not on a configured allowlist', async () => {
    mockEnv.isAllowlistConfigured = true;
    mockEnv.isAllowlisted.mockImplementation((id) => id === '+911111111111');

    await expect(
      useAuthStore.getState().signIn(baseCredential, 'ta'),
    ).rejects.toBeInstanceOf(AuthError);

    const state = useAuthStore.getState();
    expect(state.status).not.toBe('authenticated');
    expect(state.user).toBeNull();
    expect(state.tokens).toBeNull();
    // No partial session was persisted.
    expect(secureStorage.getString(StorageKeys.authTokens)).toBeNull();
  });

  it('throws the auth/not-authorized code + notAuthorized message key', async () => {
    mockEnv.isAllowlistConfigured = true;
    mockEnv.isAllowlisted.mockReturnValue(false);

    await expect(
      useAuthStore.getState().signIn(baseCredential, 'ta'),
    ).rejects.toMatchObject({ code: 'auth/not-authorized', message: 'auth.notAuthorized' });
  });

  it('checks both phone and email against the allowlist', async () => {
    mockEnv.isAllowlistConfigured = true;
    mockEnv.isAllowlisted.mockImplementation((id) => id === 'me@example.com');

    await useAuthStore
      .getState()
      .signIn({ ...baseCredential, phone: null, email: 'me@example.com' }, 'ta');

    expect(useAuthStore.getState().status).toBe('authenticated');
    expect(mockEnv.isAllowlisted).toHaveBeenCalledWith('me@example.com');
  });

  it('falls back to allowing sign-in when no allowlist is configured', async () => {
    mockEnv.isAllowlistConfigured = false;

    await useAuthStore.getState().signIn(baseCredential, 'ta');

    expect(useAuthStore.getState().status).toBe('authenticated');
    // The allow-all fallback must not even consult the (empty) allowlist.
    expect(mockEnv.isAllowlisted).not.toHaveBeenCalled();
  });
});
jest.mock('@/services/apiClient', () => ({
  api: {
    post: jest.fn(() =>
      Promise.resolve({ user: { farmer_ref: 'farmer_test_1' }, profile: null }),
    ),
  },
  configureApiAuth: jest.fn(),
}));
