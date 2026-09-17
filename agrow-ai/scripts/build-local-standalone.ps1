$paramMode = 'Usb'
if ($args.Count -gt 0) {
    $paramMode = $args[0]
}
if ($paramMode -notin @('Usb', 'Lan')) {
    throw "Mode must be 'Usb' or 'Lan'."
}

$ErrorActionPreference = 'Stop'

$env:AGROWAI_BUILD_PROFILE = 'localStandalone'
$env:EXPO_PUBLIC_APP_ENV = 'localStandalone'
if ($paramMode -eq 'Usb') {
    $env:EXPO_PUBLIC_API_BASE_URL = 'http://127.0.0.1:8000/api/v1'
    $env:EXPO_PUBLIC_DIAGNOSIS_API_BASE_URL = 'http://127.0.0.1:8000'
}
else {
    $env:EXPO_PUBLIC_API_BASE_URL = 'http://10.180.84.202:8000/api/v1'
    $env:EXPO_PUBLIC_DIAGNOSIS_API_BASE_URL = 'http://10.180.84.202:8000'
}
$env:NODE_ENV = 'production'

$projectRoot = Split-Path -Parent $PSScriptRoot
$androidRoot = Join-Path $projectRoot 'android'

Push-Location $androidRoot
try {
    & .\gradlew.bat :app:assembleLocalStandalone `
        -PreactNativeArchitectures=arm64-v8a `
        --no-daemon `
        --max-workers=2 `
        --console=plain
    if ($LASTEXITCODE -ne 0) {
        throw "Gradle localStandalone build failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
