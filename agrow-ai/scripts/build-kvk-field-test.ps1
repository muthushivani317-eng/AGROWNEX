# Builds the debug-signed, non-debuggable APK for KVK-supervised controlled field testing.
# Paddy, cotton, groundnut, chilli, and redgram require an active backend KVK override
# session, as reported by /disease/legacy-field-test/session/status, to return predictions.
$ErrorActionPreference = 'Stop'

$env:AGROWAI_BUILD_PROFILE = 'kvk_field_test'
$env:EXPO_PUBLIC_APP_ENV = 'kvk_field_test'
# FOUNDER_FULL_ACCESS is intentionally excluded: this APK is for the wider KVK
# testing group (internal testers, pilot testers, and KVK reviewers), so the
# client UI must not grant founder-only access based on who holds the device.
$env:EXPO_PUBLIC_AGROWAI_INTERNAL_FEATURE_TESTING = 'true'
$env:EXPO_PUBLIC_AGROWAI_ENABLE_ALL_TEST_ROUTES = 'true'
$env:NODE_ENV = 'production'

node scripts/validate-release-env.js
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
node scripts/security-build-gates.js --prebuild
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Push-Location android
try {
  .\gradlew.bat assembleKvkFieldTest --no-daemon --console=plain
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
  Pop-Location
}

# The APK security gate validates the non-debuggable internal-test payload; it does
# not require production signing and is therefore also applicable to kvkFieldTest.
$arm64Apk = 'android/app/build/outputs/apk/kvkFieldTest/app-arm64-v8a-kvkFieldTest.apk'
node scripts/security-build-gates.js --apk $arm64Apk
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ''
Write-Host 'KVK field-test APKs:'
Write-Host '  android/app/build/outputs/apk/kvkFieldTest/app-armeabi-v7a-kvkFieldTest.apk'
Write-Host '  android/app/build/outputs/apk/kvkFieldTest/app-arm64-v8a-kvkFieldTest.apk  <-- INSTALL THIS ON A MODERN PHYSICAL PHONE' -ForegroundColor Green
Write-Host '  android/app/build/outputs/apk/kvkFieldTest/app-x86-kvkFieldTest.apk'
Write-Host '  android/app/build/outputs/apk/kvkFieldTest/app-x86_64-kvkFieldTest.apk'

exit 0
