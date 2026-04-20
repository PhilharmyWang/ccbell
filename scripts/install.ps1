# scripts/install.ps1 — ccbell installer for Windows.
param(
    [string]$BarkKey      = "",
    [string]$DeviceName   = "",
    [string]$DeviceEmoji  = "",
    [string]$InstallDir   = "$HOME\tools\ccbell",
    [string]$Repo         = "https://github.com/PhilharmyWang/ccbell.git",
    [switch]$Offline,
    [string]$ZaiToken     = "",
    [string]$BarkServer   = ""
)

$ErrorActionPreference = "Stop"

# ── 1. Validate required parameters ──────────────────────────────────────────

if (-not $BarkKey -or -not $DeviceName -or -not $DeviceEmoji) {
    Write-Host @"

Usage:
  .\install.ps1 `
    -BarkKey "YOUR_BARK_KEY" `
    -DeviceName "MyLaptop" `
    -DeviceEmoji "💻" `
    [-InstallDir path] [-Repo url] [-Offline] `
    [-ZaiToken token] [-BarkServer url]

Required: -BarkKey, -DeviceName, -DeviceEmoji
"@
    exit 1
}

# ── 2. Python >= 3.9 ─────────────────────────────────────────────────────────

try {
    $pyVer = python --version 2>&1
} catch {
    Write-Host "ERROR: python not found. Install Python >= 3.9." -ForegroundColor Red
    exit 1
}
if ($pyVer -match '(\d+)\.(\d+)') {
    $major = [int]$Matches[1]
    $minor = [int]$Matches[2]
} else {
    Write-Host "ERROR: cannot parse python version: $pyVer" -ForegroundColor Red
    exit 1
}
if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 9)) {
    Write-Host "ERROR: Python >= 3.9 required, found $pyVer" -ForegroundColor Red
    exit 1
}
Write-Host "Python: $pyVer OK"

# ── 3. Clone / pull or offline ───────────────────────────────────────────────

if ($Offline) {
    $InstallDir = (Split-Path $PSScriptRoot -Parent)
    Write-Host "Offline mode, using repo at: $InstallDir"
} else {
    if (Test-Path "$InstallDir\.git") {
        Write-Host "Updating existing clone..."
        git -C $InstallDir pull
    } else {
        Write-Host "Cloning $Repo ..."
        git clone $Repo $InstallDir
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: git clone/pull failed" -ForegroundColor Red
        exit 1
    }
}

Push-Location $InstallDir

# ── 4. pytest ────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "Running tests..."
python -m pytest -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: tests failed" -ForegroundColor Red
    Pop-Location
    exit 1
}
Write-Host "Tests passed OK"

# ── 5. Patch settings.json ───────────────────────────────────────────────────

$dispatchPath = Join-Path $InstallDir "hooks\dispatch.py"
$patchScript  = Join-Path $InstallDir "scripts\_patch_settings.py"

$patchArgs = @(
    $patchScript,
    "--dispatch-path", $dispatchPath,
    "--bark-key",      $BarkKey,
    "--device-name",   $DeviceName,
    "--device-emoji",  $DeviceEmoji
)
if ($ZaiToken)  { $patchArgs += @("--zai-token",  $ZaiToken) }
if ($BarkServer) { $patchArgs += @("--bark-server", $BarkServer) }

python @patchArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: patch settings failed" -ForegroundColor Red
    Pop-Location
    exit 1
}

# ── 6. Smoke test ────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "Smoke test..."
Get-Content "tests\fixtures\sample_stop.json" | python "hooks\dispatch.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: smoke test returned non-zero" -ForegroundColor Yellow
} else {
    Write-Host "Smoke test passed OK"
}

Pop-Location

# ── Done ──────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "Done! 新开一个 Claude Code 会话并说一句话，iPhone 应收到通知。" -ForegroundColor Green
