#Requires -Version 5.1
<#
.SYNOPSIS
  Add tools\bd to PATH so the 'bd' command works in this project.

.DESCRIPTION
  Prepends this project's tools\bd to PATH for the current session.
  Run before using bd in a terminal, or dot-source: . .\scripts\set_bd_path.ps1

.PARAMETER Persist
  If set, adds tools\bd to the User PATH permanently (current session only by default).

.EXAMPLE
  . .\scripts\set_bd_path.ps1

.EXAMPLE
  .\scripts\set_bd_path.ps1 -Persist
#>
param(
    [switch]$Persist
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$bdDir = Join-Path $projectRoot "tools\bd"

$bdExe = Join-Path $bdDir "bd.exe"
$bdUnix = Join-Path $bdDir "bd"
if (-not ((Test-Path $bdExe) -or (Test-Path $bdUnix))) {
    Write-Error "Beads not found at $bdDir. Ensure tools/bd contains bd.exe (Windows) or bd (Unix). See docs/BEADS_INTEGRATION.md."
    exit 1
}

if ($Persist) {
    $userPath = [System.Environment]::GetEnvironmentVariable('Path', 'User')
    if ($userPath -notlike "*$bdDir*") {
        [System.Environment]::SetEnvironmentVariable('Path', "$bdDir;$userPath", 'User')
        $env:Path = "$bdDir;$env:Path"
        Write-Host "[OK] Added $bdDir to User PATH. New processes will have 'bd'." -ForegroundColor Green
    } else {
        $env:Path = "$bdDir;$env:Path"
        Write-Host "[OK] $bdDir already in User PATH. Refreshed for this session." -ForegroundColor Green
    }
} else {
    $env:Path = "$bdDir;$env:Path"
    Write-Host "[OK] Added $bdDir to PATH for this session. Run 'bd' to use Beads." -ForegroundColor Green
}

Write-Host "  bd ready     - unblocked tasks"
Write-Host "  bd create ""Title"" -p 0"
Write-Host "  bd quickstart - intro"
