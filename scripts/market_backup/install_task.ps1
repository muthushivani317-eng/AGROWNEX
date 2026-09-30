# Registers the AgrowNex market-price backup (plan 2) as a daily Windows task.
# Run once from an Administrator PowerShell in the repo root:
#     powershell -ExecutionPolicy Bypass -File scripts\market_backup\install_task.ps1
# The task runs at 03:40 every day, wakes the PC if it is asleep, and retries
# twice (at 03:55 and 04:10) if it fails.

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $here "market_backup_uploader.py"
$envFile = Join-Path $here "market_backup.env"
$python = (Get-Command python -ErrorAction Stop).Source

if (-not (Test-Path $envFile)) {
    Write-Error "Create $envFile first (AGROWNEX_API_URL and MARKET_INGEST_TOKEN)."
}

$action = New-ScheduledTaskAction -Execute $python -Argument "`"$script`"" -WorkingDirectory $here
$trigger = New-ScheduledTaskTrigger -Daily -At 3:40am
$settings = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable `
    -RestartCount 2 -RestartInterval (New-TimeSpan -Minutes 15) `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 20) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName "AgrowNex Market Price Backup" -Action $action -Trigger $trigger `
    -Settings $settings -Description "Plan 2: upload official Agmarknet 2.0 prices if the server's are stale" -Force | Out-Null

Write-Host "Installed. Test it now with:  python `"$script`" --force"
