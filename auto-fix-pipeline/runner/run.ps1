# run.ps1 — Config-driven entrypoint for the auto-fix pipeline (Epic 2).
# Loads config (YAML), resolves project root and MCP server, then invokes scripts/auto-bugfix.ps1
# with parameters derived from config. Does not replace the script; it delegates to it.
#
# Usage:
#   .\auto-fix-pipeline\runner\run.ps1
#   .\auto-fix-pipeline\runner\run.ps1 -ConfigPath "auto-fix-pipeline/config/example/homeiq-default.yaml"
#   .\auto-fix-pipeline\runner\run.ps1 -Bugs 3 -Chain
#   $env:AUTO_FIX_CONFIG = "path/to/config.yaml"; .\auto-fix-pipeline\runner\run.ps1

param(
    [string]$ConfigPath = $env:AUTO_FIX_CONFIG,
    [int]$Bugs = 5,
    [string]$Branch = "",
    [string]$TargetDir = "",
    [string]$Base = "master",
    [switch]$Chain,
    [switch]$NoDashboard,
    [switch]$NoRotate,
    [string]$TargetUnit = "",
    [switch]$Worktree
)

$ErrorActionPreference = "Stop"

# Runner lives in auto-fix-pipeline/runner/; repo root is two levels up
$RunnerDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AutoFixDir = Split-Path -Parent $RunnerDir
$ProjectRoot = Split-Path -Parent $AutoFixDir

Set-Location $ProjectRoot

# Default config path relative to repo root
if (-not $ConfigPath) {
    $ConfigPath = Join-Path $AutoFixDir "config/example/homeiq-default.yaml"
}
$configResolved = if ([System.IO.Path]::IsPathRooted($ConfigPath)) { $ConfigPath } else { Join-Path $ProjectRoot $ConfigPath }
if (-not (Test-Path $configResolved)) {
    Write-Error "Config not found: $configResolved. Set -ConfigPath or env:AUTO_FIX_CONFIG."
    exit 1
}

# Pass -ConfigPath to script so it loads config itself (Epic 3). Prefer path relative to repo root.
$scriptConfigPath = if ([System.IO.Path]::IsPathRooted($ConfigPath)) {
    try { [System.IO.Path]::GetRelativePath($ProjectRoot, $configResolved) } catch { $configResolved }
} else {
    $ConfigPath
}

# Build script arguments: hashtable for named-parameter splatting
$scriptArgs = @{
    ConfigPath = $scriptConfigPath
    Bugs       = $Bugs
    Base       = $Base
}
if ($Branch) { $scriptArgs.Branch = $Branch }
if ($TargetDir) { $scriptArgs.TargetDir = $TargetDir }
if ($Chain) { $scriptArgs.Chain = $true }
if ($NoDashboard) { $scriptArgs.NoDashboard = $true }
if ($NoRotate) { $scriptArgs.NoRotate = $true }
if ($TargetUnit) { $scriptArgs.TargetUnit = $TargetUnit }
if ($Worktree) { $scriptArgs.Worktree = $true }

$scriptPath = Join-Path $ProjectRoot "scripts/auto-bugfix.ps1"
Write-Host "Runner: invoking script with -ConfigPath $scriptConfigPath" -ForegroundColor Cyan
& $scriptPath @scriptArgs
exit $LASTEXITCODE
