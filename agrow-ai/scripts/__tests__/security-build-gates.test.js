const {
  validateEmbeddedReleaseConfig,
  validateSourceSecurityGates,
} = require('../security-build-gates');

const safe = {
  EXPO_PUBLIC_APP_ENV: 'internal_testing',
  EXPO_PUBLIC_API_BASE_URL: 'https://api.agrowai.in/api/v1',
  EXPO_PUBLIC_DIAGNOSIS_API_BASE_URL: 'https://api.agrowai.in',
  EXPO_PUBLIC_FIREBASE_API_KEY: 'public-key',
  EXPO_PUBLIC_FIREBASE_APP_ID: 'public-app-id',
  EXPO_PUBLIC_FIREBASE_PROJECT_ID: 'agrow-ai-8ba58',
  EXPO_PUBLIC_AGROWAI_INTERNAL_FEATURE_TESTING: 'true',
  EXPO_PUBLIC_AGROWAI_FOUNDER_FULL_ACCESS: 'true',
  EXPO_PUBLIC_AGROWAI_ENABLE_ALL_TEST_ROUTES: 'true',
};

describe('security build gates', () => {
  it('accepts the fail-closed internal-testing contract', () => {
    expect(validateSourceSecurityGates(safe)).toMatchObject({ profile: 'internal_testing', productionSecurityEnforced: true });
  });

  it('rejects the wrong Firebase project', () => {
    expect(() => validateSourceSecurityGates({ ...safe, EXPO_PUBLIC_FIREBASE_PROJECT_ID: 'other-project' })).toThrow('firebase_project_mismatch');
  });

  it('rejects a development OTP in internal testing', () => {
    expect(() => validateSourceSecurityGates({ ...safe, EXPO_PUBLIC_DEV_OTP: '654321' })).toThrow('static_otp_environment_forbidden');
  });

  it('rejects missing internal-testing flags', () => {
    expect(() => validateSourceSecurityGates({ ...safe, EXPO_PUBLIC_AGROWAI_INTERNAL_FEATURE_TESTING: 'false' })).toThrow('internal_testing_flags_missing');
  });

  it.each(['http://uploads.example.com/files', 'https://127.0.0.1/files'])(
    'rejects an insecure upload endpoint %s',
    (endpoint) => {
      expect(() => validateSourceSecurityGates({ ...safe, EXPO_PUBLIC_S3_UPLOAD_ENDPOINT: endpoint })).toThrow('upload_url_insecure');
    },
  );

  it('accepts production APK metadata only when internal testing is disabled', () => {
    expect(() => validateEmbeddedReleaseConfig({
      android: { package: 'com.agrowai.app' },
      extra: {
        releaseChannel: 'production',
        internalTesting: {
          enabled: false,
          allTestableFeatures: false,
          developerMocks: false,
          productionAuth: false,
          productionApi: false,
        },
      },
    }, 'production')).not.toThrow();
  });

  it('rejects internal-testing capabilities in production APK metadata', () => {
    expect(() => validateEmbeddedReleaseConfig({
      android: { package: 'com.agrowai.app' },
      extra: {
        releaseChannel: 'production',
        internalTesting: { enabled: true },
      },
    }, 'production')).toThrow('apk_production_flags_invalid');
  });
});
