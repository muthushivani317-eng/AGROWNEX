const {
  validateBuildEnvironment,
  validateHttpsPublicUrl,
} = require('../validate-release-env');

describe('build-time production environment validation', () => {
  const valid = {
    EXPO_PUBLIC_APP_ENV: 'production',
    EXPO_PUBLIC_API_BASE_URL: 'https://api.agrowai.in/api/v1',
    EXPO_PUBLIC_DIAGNOSIS_API_BASE_URL: 'https://api.agrowai.in',
    EXPO_PUBLIC_FIREBASE_API_KEY: 'public-api-key',
    EXPO_PUBLIC_FIREBASE_PROJECT_ID: 'agrowai',
    EXPO_PUBLIC_FIREBASE_APP_ID: 'public-app-id',
  };

  it('passes a complete production configuration', () => {
    expect(validateBuildEnvironment(valid)).toEqual({
      profile: 'production',
      productionSecurityEnforced: true,
    });
  });

  it.each([
    ['http://api.example/api/v1', 'api_url_insecure'],
    ['https://localhost/api/v1', 'api_url_local'],
    ['https://10.0.2.2/api/v1', 'api_url_local'],
    ['https://10.1.2.3/api/v1', 'api_url_local'],
    ['', 'api_url_missing'],
  ])('fails before packaging for unsafe URL %s', (value, category) => {
    expect(() => validateHttpsPublicUrl('api_url', value, '/api/v1')).toThrow(category);
  });

  it.each([
    ['https://api.agrowai.example/api/v2', 'api_url_contract'],
    ['https://api.agrowai.example/api/v1?debug=true', 'api_url_contract'],
    ['https://development-machine/api/v1', 'api_url_local'],
    ['https://backend.internal/api/v1', 'api_url_local'],
  ])('rejects a production URL outside the application contract: %s', (value, category) => {
    expect(() => validateHttpsPublicUrl('api_url', value, '/api/v1')).toThrow(category);
  });

  it('rejects an obsolete Railway hostname for production builds', () => {
    expect(() =>
      validateBuildEnvironment({
        ...valid,
        EXPO_PUBLIC_API_BASE_URL: 'https://agrowai-app-production.up.railway.app/api/v1',
        EXPO_PUBLIC_DIAGNOSIS_API_BASE_URL: 'https://agrowai-app-production.up.railway.app',
      }),
    ).toThrow('api_url_noncanonical');
  });

  it('allows HTTP only in an explicit non-production profile', () => {
    expect(
      validateBuildEnvironment({
        EXPO_PUBLIC_APP_ENV: 'pilot',
        EXPO_PUBLIC_API_BASE_URL: 'http://localhost:8000/api/v1',
      }),
    ).toEqual({ profile: 'pilot', productionSecurityEnforced: false });
  });

  it.each(['127.0.0.1', 'localhost'])(
    'accepts USB ADB reverse host %s only for localStandalone',
    (host) => {
      expect(
        validateBuildEnvironment({
          EXPO_PUBLIC_APP_ENV: 'localStandalone',
          EXPO_PUBLIC_API_BASE_URL: `http://${host}:8000/api/v1`,
          EXPO_PUBLIC_DIAGNOSIS_API_BASE_URL: `http://${host}:8000`,
        }),
      ).toEqual({ profile: 'localStandalone', productionSecurityEnforced: false });
    },
  );

  it('continues to accept the fixed home backend for localStandalone', () => {
    expect(
      validateBuildEnvironment({
        EXPO_PUBLIC_APP_ENV: 'localStandalone',
        EXPO_PUBLIC_API_BASE_URL: 'http://192.168.1.2:8000/api/v1',
        EXPO_PUBLIC_DIAGNOSIS_API_BASE_URL: 'http://192.168.1.2:8000',
      }),
    ).toEqual({ profile: 'localStandalone', productionSecurityEnforced: false });

  });

  it('accepts the current private hotspot backend for localStandalone', () => {
    expect(
      validateBuildEnvironment({
        EXPO_PUBLIC_APP_ENV: 'localStandalone',
        EXPO_PUBLIC_API_BASE_URL: 'http://10.180.84.202:8000/api/v1',
        EXPO_PUBLIC_DIAGNOSIS_API_BASE_URL: 'http://10.180.84.202:8000',
      }),
    ).toEqual({ profile: 'localStandalone', productionSecurityEnforced: false });
  });

  it('rejects an unapproved localStandalone host', () => {
    expect(() =>
      validateBuildEnvironment({
        EXPO_PUBLIC_APP_ENV: 'localStandalone',
        EXPO_PUBLIC_API_BASE_URL: 'http://8.8.8.8:8000/api/v1',
        EXPO_PUBLIC_DIAGNOSIS_API_BASE_URL: 'http://8.8.8.8:8000',
      }),
    ).toThrow('local_standalone_api_url_invalid');
  });

  it.each([
    'http://127.0.0.1:8000/api/v1',
    'http://api.agrowai.example/api/v1',
  ])('keeps production HTTPS enforcement unchanged for %s', (apiUrl) => {
    expect(() =>
      validateBuildEnvironment({
        ...valid,
        EXPO_PUBLIC_API_BASE_URL: apiUrl,
      }),
    ).toThrow('api_url_insecure');
  });
});
