param(
    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = "Stop"
$env:AGROWAI_AUTH_E2E_OUTPUT = $OutputPath

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $repositoryRoot "backend\.venv_crop_real_auth\Scripts\python.exe"
$runner = Join-Path $repositoryRoot "backend\scripts\run_crop_identity_auth_emulator_e2e.py"

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Validation Python environment is missing."
}

& $python $runner
if ($LASTEXITCODE -ne 0) {
    throw "Crop identity Firebase emulator validation failed."
}
