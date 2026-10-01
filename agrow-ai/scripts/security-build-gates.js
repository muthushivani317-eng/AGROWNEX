const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { loadPublicEnvironment, validateBuildEnvironment } = require('./validate-release-env');

const PROJECT_ROOT = path.resolve(__dirname, '..');
const EXPECTED_PACKAGE = 'com.agrowai.app';
const EXPECTED_FIREBASE_PROJECT = 'agrow-ai-8ba58';
const RELEASE_PROFILES = new Set(['internal_testing', 'kvk_field_test', 'production']);
const REQUIRED_FLAGS_BY_PROFILE = Object.freeze({
  internal_testing: [
    'EXPO_PUBLIC_AGROWAI_INTERNAL_FEATURE_TESTING',
    'EXPO_PUBLIC_AGROWAI_FOUNDER_FULL_ACCESS',
    'EXPO_PUBLIC_AGROWAI_ENABLE_ALL_TEST_ROUTES',
  ],
  kvk_field_test: [
    'EXPO_PUBLIC_AGROWAI_INTERNAL_FEATURE_TESTING',
    'EXPO_PUBLIC_AGROWAI_ENABLE_ALL_TEST_ROUTES',
  ],
});
const LOOPBACK_URL = /https?:\/\/(?:localhost|127(?:\.\d{1,3}){3}|0\.0\.0\.0|10\.0\.2\.2|\[?::1\]?)(?=[:/]|$)/i;

function walk(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(directory, entry.name);
    return entry.isDirectory() ? walk(full) : [full];
  });
}

function runtimeSourceFiles() {
  return ['app', 'components', 'config', 'features', 'hooks', 'lib', 'localization', 'providers', 'services']
    .map((name) => path.join(PROJECT_ROOT, name))
    .filter(fs.existsSync)
    .flatMap(walk)
    .filter((file) => /\.(?:js|jsx|ts|tsx)$/.test(file) && !file.includes(`${path.sep}__tests__${path.sep}`));
}

function validateSourceSecurityGates(values = loadPublicEnvironment(PROJECT_ROOT)) {
  const result = validateBuildEnvironment(values);
  if (!RELEASE_PROFILES.has(result.profile)) return result;
  if (values.EXPO_PUBLIC_FIREBASE_PROJECT_ID !== EXPECTED_FIREBASE_PROJECT) {
    throw new Error('firebase_project_mismatch');
  }
  if (values.EXPO_PUBLIC_DEV_OTP?.trim()) throw new Error('static_otp_environment_forbidden');
  // Anything EXPO_PUBLIC_* is readable in the APK; admin access is enforced by the server.
  // Store builds must not ship it (pilot builds may use it as a sign-in lock).
  if (result.profile === 'production' && values.EXPO_PUBLIC_ADMIN_ALLOWLIST?.trim()) {
    throw new Error('admin_allowlist_in_public_bundle');
  }
  const manifestPath = path.join(PROJECT_ROOT, 'android', 'app', 'src', 'main', 'AndroidManifest.xml');
  if (fs.existsSync(manifestPath) && !/android:allowBackup="false"/.test(fs.readFileSync(manifestPath, 'utf8'))) {
    throw new Error('android_backup_enabled');
  }
  if (values.EXPO_PUBLIC_S3_UPLOAD_ENDPOINT?.trim()) {
    let uploadUrl;
    try {
      uploadUrl = new URL(values.EXPO_PUBLIC_S3_UPLOAD_ENDPOINT);
    } catch {
      throw new Error('upload_url_invalid');
    }
    if (uploadUrl.protocol !== 'https:' || LOOPBACK_URL.test(uploadUrl.href)) {
      throw new Error('upload_url_insecure');
    }
  }
  const requiredFlags = REQUIRED_FLAGS_BY_PROFILE[result.profile] ?? [];
  for (const key of requiredFlags) {
    if (values[key] !== 'true') {
      throw new Error(`${result.profile}_flags_missing`);
    }
  }
  const offenders = runtimeSourceFiles().filter((file) => LOOPBACK_URL.test(fs.readFileSync(file, 'utf8')));
  if (offenders.length) throw new Error(`application_loopback_url:${offenders.map((f) => path.relative(PROJECT_ROOT, f)).join(',')}`);
  const packageJson = JSON.parse(fs.readFileSync(path.join(PROJECT_ROOT, 'package.json'), 'utf8'));
  const dependencies = { ...packageJson.dependencies, ...packageJson.devDependencies };
  if (dependencies['expo-dev-client'] || dependencies['expo-dev-launcher'] || dependencies['expo-dev-menu']) {
    throw new Error('developer_launcher_dependency_present');
  }
  return result;
}

function runApkAnalyzer(apkPath, args) {
  const sdkRoot = process.env.ANDROID_SDK_ROOT || process.env.ANDROID_HOME || 'D:\\Android\\Sdk';
  const analyzer = path.join(sdkRoot, 'cmdline-tools', 'latest', 'bin', 'apkanalyzer.bat');
  if (!fs.existsSync(analyzer)) throw new Error('apkanalyzer_unavailable');
  const result = spawnSync(process.env.ComSpec || 'cmd.exe', ['/d', '/s', '/c', analyzer, ...args, apkPath], {
    encoding: 'utf8',
  });
  if (result.status !== 0) throw new Error(`apkanalyzer_failed:${result.stderr.trim()}`);
  return result.stdout;
}

function validateEmbeddedReleaseConfig(parsedConfig, expectedProfile) {
  if (parsedConfig.android?.package !== EXPECTED_PACKAGE) {
    throw new Error('config_package_mismatch');
  }
  const releaseChannel = parsedConfig.extra?.releaseChannel;
  const controlledProfile = ['internal_testing', 'kvk_field_test'].includes(expectedProfile);
  if (releaseChannel !== expectedProfile) throw new Error('release_channel_mismatch');
  const flags = parsedConfig.extra?.internalTesting;
  if (controlledProfile) {
    if (!flags?.enabled || !flags?.allTestableFeatures || flags.developerMocks || !flags.productionAuth || !flags.productionApi) {
      throw new Error('apk_internal_flags_invalid');
    }
  } else if (
    flags?.enabled ||
    flags?.allTestableFeatures ||
    flags?.developerMocks ||
    flags?.productionAuth ||
    flags?.productionApi
  ) {
    throw new Error('apk_production_flags_invalid');
  }
}

function validateApkSecurityGates(apkPath, expectedProfile) {
  if (!apkPath || !fs.existsSync(apkPath)) throw new Error('apk_missing');
  const manifest = runApkAnalyzer(apkPath, ['manifest', 'print']);
  const files = runApkAnalyzer(apkPath, ['files', 'list']);
  const appConfig = runApkAnalyzer(apkPath, ['files', 'cat', '--file', 'assets/app.config']);
  const parsedConfig = JSON.parse(appConfig);
  if (!manifest.includes(`package="${EXPECTED_PACKAGE}"`)) throw new Error('apk_package_mismatch');
  if (/android:debuggable="true"/.test(manifest)) throw new Error('apk_debuggable');
  if (!/android:usesCleartextTraffic="false"/.test(manifest)) throw new Error('apk_cleartext_enabled');
  if (!/android:allowBackup="false"/.test(manifest)) throw new Error('apk_backup_enabled');
  if (/devlauncher|devmenu|expo-dev-launcher|expo-dev-menu/i.test(`${manifest}\n${files}`)) {
    throw new Error('apk_developer_launcher_present');
  }
  validateEmbeddedReleaseConfig(parsedConfig, expectedProfile);
  return { package: EXPECTED_PACKAGE, debuggable: false, developerLauncher: false };
}

if (require.main === module) {
  try {
    const values = loadPublicEnvironment(PROJECT_ROOT);
    const result = validateSourceSecurityGates(values);
    const apkIndex = process.argv.indexOf('--apk');
    if (apkIndex >= 0) {
      validateApkSecurityGates(path.resolve(PROJECT_ROOT, process.argv[apkIndex + 1]), result.profile);
    }
    console.log(`[security-build] PASS profile=${result.profile} apk_checked=${apkIndex >= 0}`);
  } catch (error) {
    console.error(`[security-build] FAIL category=${error.message}`);
    process.exitCode = 1;
  }
}

module.exports = {
  validateSourceSecurityGates,
  validateEmbeddedReleaseConfig,
  validateApkSecurityGates,
  LOOPBACK_URL,
};
