// The real native Firebase wrapper needs a live native module; stub
// getFirebaseAuth so the provider is exercised against the (globally mocked)
// @react-native-firebase/auth SDK instead of a real device.
jest.mock('@/lib/firebase', () => ({
  getFirebaseAuth: jest.fn(() => ({ __mockAuth: true })),
}));

// Avoid pulling i18next side effects into the store (same as authStore tests).
jest.mock('@/localization', () => ({
  setLanguage: jest.fn(() => Promise.resolve()),
  getLanguage: () => 'ta',
}));

// Control the access allowlist per-test. The store reads these as live property
// accesses on the shared config module, so mutating them here drives each case.
jest.mock('@/config/env', () => ({
  __esModule: true,
  ...jest.requireActual('@/config/env'),
  // The real provider only runs when Firebase is configured; force it true so
  // currentCredential()'s mock-mode short-circuit does not mask the real path.
  isFirebaseConfigured: true,
  isAllowlistConfigured: false,
  isAllowlisted: jest.fn((_id: string | null) => false),
}));

import {
  AppleAuthProvider,
  GoogleAuthProvider,
  PhoneAuthProvider,
  signInWithCredential,
  signInWithPhoneNumber,
} from '@react-native-firebase/auth';

import * as configEnv from '@/config/env';
import { getFirebaseAuth } from '@/lib/firebase';
import { initSecureStorage, secureStorage, StorageKeys } from '@/lib/storage';

import { firebaseAuthProvider } from '../services/firebaseAuthProvider';
import { useAuthStore } from '../store/authStore';
import { AuthError } from '../types';

// @react-native-firebase/auth is mocked globally in jest.setup.js.
const mockGetFirebaseAuth = getFirebaseAuth as unknown as jest.Mock;
const mockSignInWithPhone = signInWithPhoneNumber as unknown as jest.Mock;
const mockSignInWithCredential = signInWithCredential as unknown as jest.Mock;
const mockGoogleCredential = GoogleAuthProvider.credential as unknown as jest.Mock;
const mockAppleCredential = AppleAuthProvider.credential as unknown as jest.Mock;
const mockPhoneCredential = PhoneAuthProvider.credential as unknown as jest.Mock;

const mockEnv = configEnv as unknown as {
  isAllowlistConfigured: boolean;
  isAllowlisted: jest.Mock<boolean, [string | null]>;
};

const PHONE = '+919876543210';

/** A minimal native Firebase `User` shaped for `toCredential`. */
function fakeUser(overrides: Record<string, unknown> = {}) {
  return {
    uid: 'user_1',
    phoneNumber: PHONE,
    email: null,
    displayName: null,
    photoURL: null,
    refreshToken: 'refresh_1',
    getIdTokenResult: jest.fn(async () => ({
      token: 'id_token_1',
      expirationTime: new Date(Date.now() + 3_600_000).toISOString(),
    })),
    ...overrides,
  };
}

/** Make signInWithPhoneNumber resolve with a confirmation for `user`. */
function resolveWithUser(user = fakeUser()) {
  mockSignInWithPhone.mockResolvedValue({
    verificationId: 'verification_request_1',
    confirm: jest.fn(async () => ({ user })),
  });
  mockSignInWithCredential.mockResolvedValue({ user });
}

beforeAll(async () => {
  await initSecureStorage();
});

beforeEach(() => {
  // Restore the default auth stub; currentCredential tests override currentUser.
  mockGetFirebaseAuth.mockReset().mockReturnValue({ __mockAuth: true });
  mockSignInWithPhone.mockReset();
  mockSignInWithCredential.mockReset();
  mockGoogleCredential.mockClear();
  mockAppleCredential.mockClear();
  mockPhoneCredential.mockClear();
  mockEnv.isAllowlistConfigured = false;
  mockEnv.isAllowlisted.mockReset().mockReturnValue(false);
  secureStorage.remove(StorageKeys.authTokens);
  useAuthStore.setState({ status: 'initializing', user: null, tokens: null });
});

describe('firebaseAuthProvider.sendOtp — native Play Integrity (no reCAPTCHA)', () => {
  it('calls native signInWithPhoneNumber with (auth, phone) and no verifier', async () => {
    resolveWithUser();

    await firebaseAuthProvider.sendOtp(PHONE);

    // The native SDK does Play Integrity itself — no ApplicationVerifier is
    // constructed or passed (contrast the old JS-SDK omitted-verifier path).
    expect(mockSignInWithPhone).toHaveBeenCalledTimes(1);
    expect(mockSignInWithPhone).toHaveBeenCalledWith(expect.anything(), PHONE);
  });

  it('confirm() returns a phone app-credential on the correct code', async () => {
    resolveWithUser(fakeUser({ uid: 'phone_user_1' }));

    const confirmation = await firebaseAuthProvider.sendOtp(PHONE);
    const credential = await confirmation.confirm('123456');

    expect(credential.provider).toBe('phone');
    expect(credential.uid).toBe('phone_user_1');
    expect(credential.phone).toBe(PHONE);
    expect(credential.idToken).toBe('id_token_1');
    expect(credential.expiresAt).toBeGreaterThan(Date.now());
    expect(mockPhoneCredential).toHaveBeenCalledWith('verification_request_1', '123456');
    expect(mockSignInWithCredential).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        verificationId: 'verification_request_1',
        verificationCode: '123456',
      }),
    );
  });

  it('uses the matching Firebase user when Android auto-verifies before manual confirmation', async () => {
    const user = fakeUser({ uid: 'auto_verified_phone_user' });
    const auth = { currentUser: null as ReturnType<typeof fakeUser> | null };
    mockGetFirebaseAuth.mockReturnValue(auth);
    mockSignInWithPhone.mockResolvedValue({
      verificationId: 'verification_request_auto',
      confirm: jest.fn(),
    });

    const confirmation = await firebaseAuthProvider.sendOtp(PHONE);
    // Android's SMS Retriever can sign in natively between code dispatch and
    // the farmer pressing Verify.
    auth.currentUser = user;
    const credential = await confirmation.confirm('123456');

    expect(credential.uid).toBe('auto_verified_phone_user');
    expect(credential.phone).toBe(PHONE);
    expect(mockPhoneCredential).not.toHaveBeenCalled();
    expect(mockSignInWithCredential).not.toHaveBeenCalled();
  });

  it('never accepts an auto-verified Firebase user for a different phone number', async () => {
    const requestedUser = fakeUser({ uid: 'requested_phone_user' });
    const auth = {
      currentUser: fakeUser({ uid: 'other_phone_user', phoneNumber: '+919999999999' }),
    };
    mockGetFirebaseAuth.mockReturnValue(auth);
    mockSignInWithPhone.mockResolvedValue({
      verificationId: 'verification_request_requested',
      confirm: jest.fn(),
    });
    mockSignInWithCredential.mockResolvedValue({ user: requestedUser });

    const confirmation = await firebaseAuthProvider.sendOtp(PHONE);
    const credential = await confirmation.confirm('123456');

    expect(credential.uid).toBe('requested_phone_user');
    expect(mockPhoneCredential).toHaveBeenCalledWith(
      'verification_request_requested',
      '123456',
    );
  });

  it('maps a wrong code to auth/invalid-code → auth.otpIncorrect', async () => {
    mockSignInWithPhone.mockResolvedValue({
      confirm: jest.fn(async () => {
        throw { code: 'auth/invalid-verification-code' };
      }),
    });

    const confirmation = await firebaseAuthProvider.sendOtp(PHONE);
    await expect(confirmation.confirm('000000')).rejects.toMatchObject({
      code: 'auth/invalid-code',
      message: 'auth.otpIncorrect',
    });
  });

  it('maps a null confirm result (no user) to auth.otpIncorrect', async () => {
    // Native `confirm` resolves to null instead of throwing in some cases.
    mockSignInWithPhone.mockResolvedValue({ confirm: jest.fn(async () => null) });

    const confirmation = await firebaseAuthProvider.sendOtp(PHONE);
    await expect(confirmation.confirm('000000')).rejects.toMatchObject({
      code: 'auth/invalid-code',
      message: 'auth.otpIncorrect',
    });
  });

  it('does not mislabel an unknown confirmation failure as an invalid OTP', async () => {
    mockSignInWithPhone.mockResolvedValue({
      confirm: jest.fn(async () => {
        throw new Error('native confirmation failure');
      }),
    });

    const confirmation = await firebaseAuthProvider.sendOtp(PHONE);
    await expect(confirmation.confirm('000000')).rejects.toMatchObject({
      code: 'auth/otp-confirm-failed',
      message: 'auth.otpConfirmFailed',
    });
  });

  it('classifies an Android auth/unknown invalid-reCAPTCHA confirmation failure', async () => {
    mockSignInWithPhone.mockResolvedValue({
      confirm: jest.fn(async () => {
        throw {
          code: 'auth/unknown',
          message: '[auth/unknown] The request contains an invalid reCAPTCHA token.',
        };
      }),
    });

    const confirmation = await firebaseAuthProvider.sendOtp(PHONE);
    await expect(confirmation.confirm('000000')).rejects.toMatchObject({
      code: 'auth/invalid-recaptcha-token',
      message: 'auth.otpVerificationUnavailable',
    });
  });

  it('classifies the nested Android native code without retaining native details', async () => {
    mockSignInWithPhone.mockResolvedValue({
      confirm: jest.fn(async () => {
        throw {
          code: 'auth/unknown',
          nativeErrorCode: 'ERROR_INVALID_VERIFICATION_CODE',
          nativeErrorMessage: 'unsafe phone and OTP details',
        };
      }),
    });

    const confirmation = await firebaseAuthProvider.sendOtp(PHONE);
    await expect(confirmation.confirm('000000')).rejects.toMatchObject({
      code: 'auth/invalid-code',
      message: 'auth.otpIncorrect',
    });
  });

  it.each([
    ['auth/billing-not-enabled', 'auth.otpBillingRequired'],
    ['auth/operation-not-allowed', 'auth.otpPhoneSignInDisabled'],
  ])('maps confirm failure %s to %s', async (code, messageKey) => {
    mockSignInWithPhone.mockResolvedValue({
      confirm: jest.fn(async () => {
        throw { code };
      }),
    });

    const confirmation = await firebaseAuthProvider.sendOtp(PHONE);
    await expect(confirmation.confirm('000000')).rejects.toMatchObject({
      code,
      message: messageKey,
    });
  });
});

describe('firebaseAuthProvider.sendOtp — failures surface, never silent', () => {
  it.each([
    ['auth/invalid-phone-number', 'auth.invalidPhone'],
    ['auth/too-many-requests', 'auth.otpQuotaExceeded'],
    ['auth/quota-exceeded', 'auth.otpQuotaExceeded'],
    ['auth/billing-not-enabled', 'auth.otpBillingRequired'],
    ['auth/operation-not-allowed', 'auth.otpPhoneSignInDisabled'],
    ['auth/network-request-failed', 'auth.otpNetworkError'],
    ['auth/app-not-authorized', 'auth.otpVerificationUnavailable'],
    ['auth/missing-client-identifier', 'auth.otpVerificationUnavailable'],
    ['auth/invalid-app-credential', 'auth.otpVerificationUnavailable'],
    ['auth/captcha-check-failed', 'auth.otpVerificationUnavailable'],
    ['auth/internal-error', 'auth.otpSendFailed'],
  ])('maps %s to a translatable AuthError (%s)', async (code, messageKey) => {
    mockSignInWithPhone.mockRejectedValue({ code });

    await expect(firebaseAuthProvider.sendOtp(PHONE)).rejects.toMatchObject({
      code,
      message: messageKey,
    });
    // Must be an AuthError so the LoginScreen renders a specific message.
    await expect(firebaseAuthProvider.sendOtp(PHONE)).rejects.toBeInstanceOf(AuthError);
  });

  it('maps an unknown/codeless failure to auth.otpSendFailed', async () => {
    mockSignInWithPhone.mockRejectedValue(new Error('network exploded'));

    await expect(firebaseAuthProvider.sendOtp(PHONE)).rejects.toMatchObject({
      code: 'auth/otp-send-failed',
      message: 'auth.otpSendFailed',
    });
  });

  it('maps Firebase status 17202 invalid reCAPTCHA token to app verification unavailable', async () => {
    mockSignInWithPhone.mockRejectedValue({
      code: 'auth/unknown',
      message: '[auth/unknown] The request contains an invalid reCAPTCHA token.',
    });

    await expect(firebaseAuthProvider.sendOtp(PHONE)).rejects.toMatchObject({
      code: 'auth/invalid-recaptcha-token',
      message: 'auth.otpVerificationUnavailable',
    });
  });
});

describe('social sign-in exchanges the OIDC token via the native SDK', () => {
  it('signInWithGoogle exchanges the Google id token for a Firebase credential', async () => {
    mockSignInWithCredential.mockResolvedValue({ user: fakeUser({ uid: 'g_1', email: 'f@x.com' }) });

    const credential = await firebaseAuthProvider.signInWithGoogle('google-id-token');

    expect(mockGoogleCredential).toHaveBeenCalledWith('google-id-token');
    expect(mockSignInWithCredential).toHaveBeenCalledTimes(1);
    expect(credential.provider).toBe('google');
    expect(credential.uid).toBe('g_1');
  });

  it('signInWithApple passes (identityToken, rawNonce) positionally to AppleAuthProvider', async () => {
    mockSignInWithCredential.mockResolvedValue({ user: fakeUser({ uid: 'a_1' }) });

    const credential = await firebaseAuthProvider.signInWithApple({
      identityToken: 'apple-id-token',
      rawNonce: 'raw-nonce',
      email: null,
      fullName: null,
    });

    expect(mockAppleCredential).toHaveBeenCalledWith('apple-id-token', 'raw-nonce');
    expect(credential.provider).toBe('apple');
    expect(credential.uid).toBe('a_1');
  });
});

describe('firebaseAuthProvider.refreshToken — network failure vs. session invalid', () => {
  it('returns null (session invalid) for a genuine invalidation code', async () => {
    const user = fakeUser({
      getIdTokenResult: jest.fn(async () => {
        throw { code: 'auth/user-token-expired' };
      }),
    });
    mockGetFirebaseAuth.mockReturnValue({ currentUser: user });

    const result = await firebaseAuthProvider.refreshToken('refresh_1');
    expect(result).toBeNull();
  });

  it('throws a distinct transient error for a dropped connection, instead of returning null', async () => {
    const user = fakeUser({
      getIdTokenResult: jest.fn(async () => {
        throw { code: 'auth/network-request-failed' };
      }),
    });
    mockGetFirebaseAuth.mockReturnValue({ currentUser: user });

    await expect(firebaseAuthProvider.refreshToken('refresh_1')).rejects.toMatchObject({
      code: 'auth/transient-refresh-failure',
    });
  });

  it('throws the same transient error for an unrecognized failure code', async () => {
    const user = fakeUser({
      getIdTokenResult: jest.fn(async () => {
        throw { code: 'auth/some-unexpected-native-error' };
      }),
    });
    mockGetFirebaseAuth.mockReturnValue({ currentUser: user });

    await expect(firebaseAuthProvider.refreshToken('refresh_1')).rejects.toMatchObject({
      code: 'auth/transient-refresh-failure',
    });
  });
});

describe('phone sign-in still enforces the admin allowlist', () => {
  it('rejects a phone credential that is not on the configured allowlist', async () => {
    mockEnv.isAllowlistConfigured = true;
    mockEnv.isAllowlisted.mockReturnValue(false); // number not permitted
    resolveWithUser();

    // Full provider path: dispatch OTP → confirm code → hand credential to signIn.
    const confirmation = await firebaseAuthProvider.sendOtp(PHONE);
    const credential = await confirmation.confirm('123456');

    await expect(
      useAuthStore.getState().signIn(credential, 'ta'),
    ).rejects.toMatchObject({ code: 'auth/not-authorized' });

    const state = useAuthStore.getState();
    expect(state.status).not.toBe('authenticated');
    expect(state.user).toBeNull();
    expect(secureStorage.getString(StorageKeys.authTokens)).toBeNull();
  });

  it('admits a phone credential that IS on the allowlist', async () => {
    mockEnv.isAllowlistConfigured = true;
    mockEnv.isAllowlisted.mockImplementation((id) => id === PHONE);
    resolveWithUser();

    const confirmation = await firebaseAuthProvider.sendOtp(PHONE);
    const credential = await confirmation.confirm('123456');
    await useAuthStore.getState().signIn(credential, 'ta');

    expect(useAuthStore.getState().status).toBe('authenticated');
    expect(mockEnv.isAllowlisted).toHaveBeenCalledWith(PHONE);
  });
});
jest.mock('@/services/apiClient', () => ({
  api: { post: jest.fn(() => Promise.resolve({ data: {} })) },
  configureApiAuth: jest.fn(),
}));
