/** @type {import('jest').Config} */
module.exports = {
  preset: 'jest-expo',
  // Default is 5000ms. Editing this config file busts Jest's babel transform
  // cache (it's keyed on the config's hash), so the FIRST run after any
  // jest.config.js change recompiles the entire dependency graph from
  // scratch -- on a loaded machine that can push individual interaction
  // tests (render + act + press) past the 5s default even though nothing
  // is actually hanging (no unresolved promises/timers were found in
  // DistrictSelector/CropSelector/FarmSelector's press handlers -- all are
  // plain synchronous useState updates). Raised as a safety margin so a
  // cold cache (fresh checkout, `jest --clearCache`, CI) doesn't produce
  // phantom timeout failures (2026-08 pre-release audit).
  testTimeout: 15000,
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
  transformIgnorePatterns: [
    // standard-navigation ships untranspiled ESM (`import ... from`) and is a
    // real dependency of expo-router -- any test that imports a screen using
    // expo-router's useRouter/Link/etc. pulls it in transitively. Without it
    // in this allowlist Jest leaves it untransformed and every such test
    // suite fails to even load (2026-08 pre-release audit: caught by
    // friendlyDiagnosisError.test.ts, but would affect any expo-router-using
    // screen test).
    'node_modules/(?!((jest-)?react-native|@react-native(-community)?|expo(nent)?|@expo(nent)?/.*|@expo-google-fonts/.*|expo-router|standard-navigation|react-navigation|@react-navigation/.*|@unimodules/.*|unimodules|sentry-expo|native-base|react-native-svg|nativewind|react-native-css-interop|lucide-react-native|@react-native-firebase/.*|uuid))',
  ],
  collectCoverageFrom: [
    'features/**/*.{ts,tsx}',
    'components/**/*.{ts,tsx}',
    'lib/**/*.{ts,tsx}',
    'utils/**/*.{ts,tsx}',
    '!**/index.ts',
    '!**/*.d.ts',
  ],
};
