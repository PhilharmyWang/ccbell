# scripts/uninstall.ps1 — Remove ccbell hooks & env from Claude Code settings.json.
param(
    [string]$SettingsPath = ""
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path $PSScriptRoot -Parent
$uninstallPy = Join-Path $scriptDir "scripts\_uninstall_settings.py"

$pyArgs = @($uninstallPy)
if ($SettingsPath) {
    $pyArgs += @("--settings-path", $SettingsPath)
}

python @pyArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: uninstall failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "ccbell has been uninstalled. You may also delete the repo directory if desired." -ForegroundColor Green
