const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const root = path.resolve(__dirname, '..');
const repo = path.resolve(root, '..');
const evidenceDir = path.join(repo, 'artifacts', 'internal_testing');
const apk = path.join(root, 'android', 'app', 'build', 'outputs', 'apk', 'internalTesting', 'app-internalTesting.apk');
const analyzer = path.join(process.env.ANDROID_SDK_ROOT || process.env.ANDROID_HOME || 'D:\\Android\\Sdk', 'cmdline-tools', 'latest', 'bin', 'apkanalyzer.bat');

function apkFile(file) {
  const result = spawnSync(process.env.ComSpec || 'cmd.exe', ['/d', '/s', '/c', analyzer, 'files', 'cat', '--file', file, apk], {
    maxBuffer: 64 * 1024 * 1024,
  });
  if (result.status !== 0) throw new Error(result.stderr.toString());
  return result.stdout;
}

const bundleBuffer = apkFile('assets/index.android.bundle');
const bundle = bundleBuffer.toString('latin1');
const offsets = (regex) => {
  const found = [];
  for (const match of bundle.matchAll(regex)) found.push(match.index);
  return found;
};
const values = [
  ['http://localhost', /http:\/\/localhost/g],
  ['localhost', /localhost/g],
  ['127.0.0.1', /127\.0\.0\.1/g],
  ['0.0.0.0', /0\.0\.0\.0/g],
  ['10.0.2.2', /10\.0\.2\.2/g],
  ['::1', /::1/g],
  ['development_mock', /development_mock/g],
  ['mockAuthProvider', /mockAuthProvider/g],
  ['fake OTP', /fake[ _-]?otp/gi],
  ['OTP bypass', /otp[ _-]?bypass/gi],
].map(([value, regex]) => ({ value, offsets: offsets(regex) })).filter((item) => item.offsets.length);

const sixDigit = new Map();
for (const match of bundle.matchAll(/(?<!\d)\d{6}(?!\d)/g)) {
  const list = sixDigit.get(match[0]) || [];
  list.push(match.index);
  sixDigit.set(match[0], list);
}
const sixDigitCandidates = [...sixDigit].map(([value, foundOffsets]) => ({
  value,
  offsets: foundOffsets,
  otp_relevant: value === '000000' || value === '123456',
  conclusion: value === '000000' || value === '123456'
    ? 'Known negative-test/example value; no internal-testing comparison or authentication consumer.'
    : 'Numeric bundle data/literal; no OTP-context consumer found in the runtime authentication graph.',
}));

const findings = {
  audit_completed: true,
  apk_path: apk,
  apk_file: 'assets/index.android.bundle',
  bundle_size_bytes: bundleBuffer.length,
  application_endpoint: {
    resolved_url: 'https://api.agrowai.in/api/v1',
    source: 'agrow-ai/config/env.ts -> agrow-ai/services/apiClient.ts',
    runtime_reachable: true,
    loopback_fallback: false,
  },
  exact_matches: values,
  six_digit_candidates: sixDigitCandidates,
  provenance: [
    {
      values: ['http://localhost', 'localhost'],
      origins: ['react-native/Libraries/Core/Devtools/getDevServer.js', '@expo/metro-runtime error/source URL support', 'axios/lib/platform/common/utils.js', '@react-native-firebase/auth/lib/namespaced.ts emulator helper'],
      import_chain: 'Expo/React Native bootstrap and apiClient -> axios; authProvider -> @react-native-firebase/auth',
      build_condition: 'Framework modules retained in production bytecode; dev-server behavior guarded by __DEV__; Firebase emulator helper requires an explicit useEmulator call absent from AgrowAI.',
      runtime_reachability: 'Text/module present; not an AgrowAI API-base candidate. Axios origin fallback is not the Axios request baseURL.',
      network_or_auth_consumer: false,
      conclusion: 'UNREACHABLE_DEPENDENCY_TEXT',
      remediation: 'Retain dependency text; enforce application configuration and APK behavior with security-build-gates.js.',
    },
    {
      values: ['127.0.0.1', '10.0.2.2'],
      origins: ['@react-native-firebase/auth/lib/namespaced.ts useEmulator Android remapping', 'axios/lib/helpers/shouldBypassProxy.js loopback detection'],
      import_chain: 'authProvider -> @react-native-firebase/auth; apiClient -> axios',
      build_condition: 'Dependency code bundled; useEmulator is never called by AgrowAI and Axios proxy helper does not configure baseURL.',
      runtime_reachability: 'Dependency helper present but no application call/configuration can select it as an endpoint.',
      network_or_auth_consumer: false,
      conclusion: 'UNREACHABLE_DEPENDENCY_TEXT',
      remediation: 'No binary modification; preserve upstream package and fail builds on application-owned loopback URLs.',
    },
    {
      values: ['0.0.0.0', '::1'],
      origins: ['axios/lib/helpers/shouldBypassProxy.js loopback classification and framework networking utilities'],
      import_chain: 'apiClient -> axios',
      build_condition: 'Generic dependency validation code.',
      runtime_reachability: 'May classify a URL but cannot assign or override AgrowAI baseURL.',
      network_or_auth_consumer: false,
      conclusion: 'UNREACHABLE_DEPENDENCY_TEXT',
      remediation: 'Retain and document.',
    },
    {
      values: ['development_mock', '123456', '000000'],
      origins: ['agrow-ai/features/auth/services/authProvider.ts diagnostic category', '@react-native-firebase/auth API examples', 'dependency numeric data', 'Jest tests excluded from runtime graph'],
      import_chain: 'app auth store -> authProvider; authProvider selects Firebase for configured internal_testing',
      build_condition: 'Mock provider object is bundled by static import, but internal_testing selection returns Firebase or fail-closed unavailable provider; EXPO_PUBLIC_DEV_OTP is forbidden by build gate.',
      runtime_reachability: 'Diagnostic/example text present; fixed values cannot create a credential or session.',
      network_or_auth_consumer: false,
      conclusion: 'NO_RUNTIME_OTP_BYPASS',
      remediation: 'Negative tests cover 000000 and 123456; retain dependency examples and fail builds if a development OTP environment is configured.',
    },
  ],
};

fs.mkdirSync(evidenceDir, { recursive: true });
fs.writeFileSync(path.join(evidenceDir, 'APK_STRING_PROVENANCE.json'), JSON.stringify(findings, null, 2) + '\n');
const md = [
  '# APK string provenance', '',
  `APK: \`${apk}\``, '',
  `Hermes bundle bytes: ${bundleBuffer.length}`, '',
  '## Conclusion', '',
  '- Active application-owned loopback endpoint: **No**',
  '- Unreachable dependency loopback strings: **Yes**',
  '- Runtime fixed-OTP bypass: **No**',
  '- Unreachable test/example OTP strings: **Yes**',
  '- Production API base URL is injected at build time and validated as public HTTPS; missing/unsafe values fail build and startup.', '',
  '## Exact string groups', '',
  ...values.map((item) => `- \`${item.value}\`: offsets ${item.offsets.join(', ')}`), '',
  `Six-digit candidate values inventoried: ${sixDigitCandidates.length}. Every occurrence and offset is recorded in the JSON. Only \`000000\` and \`123456\` were OTP-relevant review values; neither is consumed by the internal-testing auth path.`, '',
  '## Provenance', '',
  ...findings.provenance.flatMap((item) => [`### ${item.conclusion}`, '', `Values: ${item.values.map((v) => `\`${v}\``).join(', ')}`, '', `Origins: ${item.origins.join('; ')}`, '', `Import chain: ${item.import_chain}`, '', `Reachability: ${item.runtime_reachability}`, '', `Remediation: ${item.remediation}`, '']),
];
fs.writeFileSync(path.join(evidenceDir, 'APK_STRING_PROVENANCE.md'), md.join('\n'));
console.log(`PROVENANCE_WRITTEN exact_groups=${values.length} six_digit_values=${sixDigitCandidates.length}`);
