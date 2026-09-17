$ErrorActionPreference = 'Stop'

$env:AGROWAI_BUILD_PROFILE = 'internal_testing'
$env:EXPO_PUBLIC_APP_ENV = 'internal_testing'
$env:EXPO_PUBLIC_AGROWAI_INTERNAL_FEATURE_TESTING = 'true'
$env:EXPO_PUBLIC_AGROWAI_FOUNDER_FULL_ACCESS = 'true'
$env:EXPO_PUBLIC_AGROWAI_ENABLE_ALL_TEST_ROUTES = 'true'
$env:NODE_ENV = 'production'

node scripts/validate-release-env.js
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
node scripts/security-build-gates.js --prebuild
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Push-Location android
try {
  .\gradlew.bat assembleInternalTesting --no-daemon --console=plain
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
  Pop-Location
}

# ABI splitting produces per-architecture APK filenames instead of one universal APK.
node scripts/security-build-gates.js --apk android/app/build/outputs/apk/internalTesting/app-arm64-v8a-internalTesting.apk
exit $LASTEXITCODE
