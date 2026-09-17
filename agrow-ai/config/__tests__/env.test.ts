/**
 * Unit tests for the admin access-allowlist helpers. The allowlist is parsed
 * from EXPO_PUBLIC_ADMIN_ALLOWLIST at module load, so each case re-imports the
 * module in isolation with the env var set to the value under test.
 */
const withAllowlist = (value: string, fn: (env: typeof import('../env')) => void) => {
  jest.isolateModules(() => {
    const prev = process.env.EXPO_PUBLIC_ADMIN_ALLOWLIST;
    process.env.EXPO_PUBLIC_ADMIN_ALLOWLIST = value;
    try {
      fn(require('../env'));
    } finally {
      if (prev === undefined) delete process.env.EXPO_PUBLIC_ADMIN_ALLOWLIST;
      else process.env.EXPO_PUBLIC_ADMIN_ALLOWLIST = prev;
    }
  });
};

describe('admin allowlist config', () => {
  it('treats a blank/unset value as unconfigured (allow-all upstream)', () => {
    withAllowlist('', (env) => {
      expect(env.isAllowlistConfigured).toBe(false);
      expect(env.adminAllowlist).toEqual([]);
      // Membership is false even for a plausible identity: callers must treat
      // "not configured" as allow-all, never call isAllowlisted() as a gate.
      expect(env.isAllowlisted('+919999999999')).toBe(false);
    });
  });

  it('parses, trims and lower-cases entries', () => {
    withAllowlist(' +919999999999 , Me@Example.com ,', (env) => {
      expect(env.isAllowlistConfigured).toBe(true);
      expect(env.adminAllowlist).toEqual(['+919999999999', 'me@example.com']);
    });
  });

  it('matches case-insensitively and ignores surrounding whitespace', () => {
    withAllowlist('+919999999999,me@example.com', (env) => {
      expect(env.isAllowlisted('+919999999999')).toBe(true);
      expect(env.isAllowlisted('  ME@EXAMPLE.COM ')).toBe(true);
      expect(env.isAllowlisted('someone-else@example.com')).toBe(false);
      expect(env.isAllowlisted(null)).toBe(false);
      expect(env.isAllowlisted('')).toBe(false);
    });
  });
});

/**
 * Runtime sanity check. Each EXPO_PUBLIC_* key is read via a static reference;
 * in the Jest transform these resolve to live `process.env` reads, so setting a
 * var before calling the function is observed. We snapshot and restore the keys
 * we touch so the cases stay isolated.
 */
describe('missingPublicEnvKeys', () => {
  const KEYS = [
    'EXPO_PUBLIC_API_BASE_URL',
    'EXPO_PUBLIC_FIREBASE_API_KEY',
    'EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN',
    'EXPO_PUBLIC_FIREBASE_PROJECT_ID',
    'EXPO_PUBLIC_FIREBASE_STORAGE_BUCKET',
    'EXPO_PUBLIC_FIREBASE_MESSAGING_SENDER_ID',
    'EXPO_PUBLIC_FIREBASE_APP_ID',
    'EXPO_PUBLIC_ADMIN_ALLOWLIST',
    'EXPO_PUBLIC_MAPBOX_TOKEN',
  ] as const;

  const withEnv = (values: Partial<Record<(typeof KEYS)[number], string>>, fn: () => void) => {
    const prev = new Map(KEYS.map((k) => [k, process.env[k]]));
    for (const k of KEYS) delete process.env[k];
    Object.assign(process.env, values);
    try {
      fn();
    } finally {
      for (const k of KEYS) {
        const v = prev.get(k);
        if (v === undefined) delete process.env[k];
        else process.env[k] = v;
      }
    }
  };

  it('reports every expected key when none are set', () => {
    withEnv({}, () => {
      const { missingPublicEnvKeys } = require('../env');
      expect(missingPublicEnvKeys()).toEqual([...KEYS]);
    });
  });

  it('treats a whitespace-only value as missing', () => {
    withEnv({ EXPO_PUBLIC_MAPBOX_TOKEN: '   ' }, () => {
      const { missingPublicEnvKeys } = require('../env');
      expect(missingPublicEnvKeys()).toContain('EXPO_PUBLIC_MAPBOX_TOKEN');
    });
  });

  it('omits keys that have a real value and never leaks the value', () => {
    withEnv(
      {
        EXPO_PUBLIC_API_BASE_URL: 'https://api.example.com',
        EXPO_PUBLIC_FIREBASE_API_KEY: 'AIza-secret',
      },
      () => {
        const { missingPublicEnvKeys } = require('../env');
        const missing = missingPublicEnvKeys();
        expect(missing).not.toContain('EXPO_PUBLIC_API_BASE_URL');
        expect(missing).not.toContain('EXPO_PUBLIC_FIREBASE_API_KEY');
        // Only key names are ever returned, never the values.
        expect(missing.join(',')).not.toContain('AIza-secret');
        expect(missing).toContain('EXPO_PUBLIC_FIREBASE_APP_ID');
      },
    );
  });
});

describe('production endpoint security', () => {
  const validProduction = {
    profile: 'production' as const,
    apiBaseUrl: 'https://api.agrowai.example/api/v1',
    diagnosisApiBaseUrl: 'https://diagnosis.agrowai.example',
    firebaseConfigured: true,
  };

  it('accepts valid public HTTPS production URLs', () => {
    const { getReleaseEnvironmentError } = require('../env');
    expect(getReleaseEnvironmentError(validProduction)).toBeNull();
  });

  it.each([
    ['HTTP', 'http://api.agrowai.example/api/v1', 'api_url_insecure'],
    ['localhost', 'https://localhost:8000/api/v1', 'api_url_local'],
    ['emulator loopback', 'https://10.0.2.2:8000/api/v1', 'api_url_local'],
    ['LAN address', 'https://192.168.1.20:8000/api/v1', 'api_url_local'],
    ['missing URL', '', 'api_url_missing'],
  ])('rejects %s in production', (_label, apiBaseUrl, expected) => {
    const { getReleaseEnvironmentError } = require('../env');
    expect(getReleaseEnvironmentError({ ...validProduction, apiBaseUrl })).toBe(expected);
  });

  it('accepts local HTTP for the explicit development profile', () => {
    const { getReleaseEnvironmentError } = require('../env');
    expect(
      getReleaseEnvironmentError({
        profile: 'development',
        apiBaseUrl: 'http://localhost:8000/api/v1',
        diagnosisApiBaseUrl: 'http://localhost:8000',
        firebaseConfigured: false,
      }),
    ).toBeNull();
  });

  it('accepts local HTTP for the explicit non-production pilot profile', () => {
    const { getReleaseEnvironmentError } = require('../env');
    expect(
      getReleaseEnvironmentError({
        profile: 'pilot',
        apiBaseUrl: 'http://192.168.1.20:8000/api/v1',
        diagnosisApiBaseUrl: 'http://192.168.1.20:8000',
        firebaseConfigured: true,
      }),
    ).toBeNull();
  });
});
