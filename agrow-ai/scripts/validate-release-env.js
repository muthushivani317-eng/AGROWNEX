const fs = require('node:fs');
const path = require('node:path');

const VALID_PROFILES = new Set([
  'development',
  'pilot',
  'localStandalone',
  'internal_testing',
  'kvk_field_test',
  'production',
]);
const PRODUCTION_SECURITY_PROFILES = new Set(['internal_testing', 'kvk_field_test', 'production']);
const PRODUCTION_API_HOSTNAME = 'api.agrowai.in';
const LOCAL_STANDALONE_HOSTS = new Set(['127.0.0.1', 'localhost']);

function validateLocalStandaloneUrl(name, value, expectedPath) {
  if (!value || !value.trim()) throw new Error(`${name}_invalid`);
  let parsed;
  try {
    parsed = new URL(value);
  } catch {
    throw new Error(`${name}_invalid`);
  }
  const hostname = parsed.hostname.toLowerCase();
  const normalizedPath = parsed.pathname.replace(/\/+$/, '') || '/';
  if (
    parsed.protocol !== 'http:' ||
    parsed.port !== '8000' ||
    !(LOCAL_STANDALONE_HOSTS.has(hostname) || isPrivateIpv4(hostname)) ||
    normalizedPath !== expectedPath ||
    parsed.search ||
    parsed.hash
  ) {
    throw new Error(`${name}_invalid`);
  }
}
const LOCAL_HOSTS = new Set(['localhost', '127.0.0.1', '10.0.2.2', '::1']);

function parseEnvFile(filePath) {
  if (!fs.existsSync(filePath)) return {};
  const values = {};
  for (const rawLine of fs.readFileSync(filePath, 'utf8').split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;
    const match = /^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$/.exec(line);
    if (!match) continue;
    let value = match[2].trim();
    if (
      value.length >= 2 &&
      ((value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'")))
    ) {
      value = value.slice(1, -1);
    }
    values[match[1]] = value;
  }
  return values;
}

function loadPublicEnvironment(projectRoot = path.resolve(__dirname, '..')) {
  const base = parseEnvFile(path.join(projectRoot, '.env'));
  const provisionalProfile =
    process.env.AGROWAI_BUILD_PROFILE ||
    process.env.EXPO_PUBLIC_APP_ENV ||
    process.env.APP_ENV ||
    base.EXPO_PUBLIC_APP_ENV ||
    'production';
  const profile = VALID_PROFILES.has(provisionalProfile) ? provisionalProfile : 'production';
  return {
    ...base,
    ...parseEnvFile(path.join(projectRoot, '.env.local')),
    ...parseEnvFile(path.join(projectRoot, `.env.${profile}`)),
    ...parseEnvFile(path.join(projectRoot, `.env.${profile}.local`)),
    ...process.env,
    EXPO_PUBLIC_APP_ENV: profile,
  };
}

function isPrivateIpv4(hostname) {
  const octets = hostname.split('.').map(Number);
  if (
    octets.length !== 4 ||
    octets.some((part) => !Number.isInteger(part) || part < 0 || part > 255)
  ) {
    return false;
  }
  return (
    octets[0] === 10 ||
    octets[0] === 127 ||
    (octets[0] === 169 && octets[1] === 254) ||
    (octets[0] === 172 && octets[1] >= 16 && octets[1] <= 31) ||
    (octets[0] === 192 && octets[1] === 168)
  );
}

function validateHttpsPublicUrl(name, value, expectedPath) {
  if (!value || !value.trim()) throw new Error(`${name}_missing`);
  let parsed;
  try {
    parsed = new URL(value);
  } catch {
    throw new Error(`${name}_invalid`);
  }
  if (parsed.protocol !== 'https:') throw new Error(`${name}_insecure`);
  const hostname = parsed.hostname.toLowerCase().replace(/^\[|\]$/g, '');
  if (
    LOCAL_HOSTS.has(hostname) ||
    isPrivateIpv4(hostname) ||
    hostname.endsWith('.local') ||
    hostname.endsWith('.lan') ||
    hostname.endsWith('.internal') ||
    hostname.endsWith('.test') ||
    !hostname.includes('.')
  ) {
    throw new Error(`${name}_local`);
  }
  const normalizedPath = parsed.pathname.replace(/\/+$/, '') || '/';
  if (
    normalizedPath !== expectedPath ||
    parsed.username ||
    parsed.password ||
    parsed.search ||
    parsed.hash ||
    (parsed.port && parsed.port !== '443')
  ) {
    throw new Error(`${name}_contract`);
  }
}

function validateBuildEnvironment(values = loadPublicEnvironment()) {
  const profile = values.EXPO_PUBLIC_APP_ENV;
  if (!VALID_PROFILES.has(profile)) throw new Error('build_profile_invalid');
  if (profile === 'localStandalone') {
    validateLocalStandaloneUrl(
      'local_standalone_api_url',
      values.EXPO_PUBLIC_API_BASE_URL,
      '/api/v1',
    );
    validateLocalStandaloneUrl(
      'local_standalone_diagnosis_url',
      values.EXPO_PUBLIC_DIAGNOSIS_API_BASE_URL,
      '/',
    );
    return { profile, productionSecurityEnforced: false };
  }
  if (!PRODUCTION_SECURITY_PROFILES.has(profile)) {
    return { profile, productionSecurityEnforced: false };
  }

  validateHttpsPublicUrl('api_url', values.EXPO_PUBLIC_API_BASE_URL, '/api/v1');
  validateHttpsPublicUrl('diagnosis_url', values.EXPO_PUBLIC_DIAGNOSIS_API_BASE_URL, '/');
  if (profile === 'production') {
    if (new URL(values.EXPO_PUBLIC_API_BASE_URL).hostname !== PRODUCTION_API_HOSTNAME) {
      throw new Error('api_url_noncanonical');
    }
    if (new URL(values.EXPO_PUBLIC_DIAGNOSIS_API_BASE_URL).hostname !== PRODUCTION_API_HOSTNAME) {
      throw new Error('diagnosis_url_noncanonical');
    }
  }
  for (const key of [
    'EXPO_PUBLIC_FIREBASE_API_KEY',
    'EXPO_PUBLIC_FIREBASE_PROJECT_ID',
    'EXPO_PUBLIC_FIREBASE_APP_ID',
  ]) {
    if (!values[key] || !values[key].trim()) throw new Error('firebase_missing');
  }
  return { profile, productionSecurityEnforced: true };
}

if (require.main === module) {
  try {
    const result = validateBuildEnvironment();
    console.log(
      `[release-env] PASS profile=${result.profile} https_required=${result.productionSecurityEnforced}`,
    );
  } catch (error) {
    console.error(`[release-env] FAIL category=${error.message}`);
    process.exitCode = 1;
  }
}

module.exports = { loadPublicEnvironment, validateBuildEnvironment, validateHttpsPublicUrl };
