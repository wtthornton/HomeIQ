# Verify Core Stack (Epic 31 pipeline)
# Brings up influxdb -> websocket-ingestion -> data-api -> admin-api -> health-dashboard
# and verifies health/stats endpoints to fix Dashboard 502 / Degraded.
# Usage: .\scripts\verify-core-stack.ps1 [-StartOnly] [-SkipStart]

param(
    [switch]$StartOnly,
    [switch]$SkipStart
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Push-Location $projectRoot
$coreServices = @("influxdb", "websocket-ingestion", "data-api", "admin-api", "health-dashboard")

function Test-Url {
    param([string]$Uri, [int]$TimeoutSec = 10, [switch]$ReturnCodeOnError)
    try {
        $r = Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec $TimeoutSec
        return $r.StatusCode
    } catch {
        if ($ReturnCodeOnError -and $_.Exception.Response) {
            return [int]$_.Exception.Response.StatusCode
        }
        return $null
    }
}

function Get-Status {
    param([int]$Code)
    if ($Code -eq 200) { return "OK" }
    if ($null -eq $Code) { return "FAIL" }
    return "HTTP$Code"
}

Write-Host "=== HomeIQ Core Stack Verification ===" -ForegroundColor Cyan
Write-Host ""

if (-not $SkipStart) {
    Write-Host "Starting core services: $($coreServices -join ', ')" -ForegroundColor Yellow
    docker compose up -d $coreServices 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to start services." -ForegroundColor Red
        Pop-Location
        exit 1
    }
    Write-Host "Waiting for services to be healthy (up to 90s)..." -ForegroundColor Yellow
    $wait = 0
    while ($wait -lt 90) {
        $hc = Test-Url -Uri "http://localhost:8004/health" -TimeoutSec 5
        if ($hc -eq 200) { break }
        Start-Sleep -Seconds 5
        $wait += 5
    }
    if ((Test-Url -Uri "http://localhost:8004/health" -TimeoutSec 5) -ne 200) {
        Write-Host "Admin API did not become healthy in time. Check: docker compose logs admin-api" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    Write-Host "Core services started." -ForegroundColor Green
    Write-Host ""
}

if ($StartOnly) { exit 0 }

Write-Host "Verifying endpoints..." -ForegroundColor Yellow
$checks = @(
    @{ Name = "InfluxDB";           Url = "http://localhost:8086/health"; Allow401 = $false },
    @{ Name = "WebSocket Ingestion"; Url = "http://localhost:8001/health"; Allow401 = $false },
    @{ Name = "Data API";           Url = "http://localhost:8006/health"; Allow401 = $false },
    @{ Name = "Admin API (root)";   Url = "http://localhost:8004/health"; Allow401 = $false },
    @{ Name = "Admin API (v1/health)"; Url = "http://localhost:8004/api/v1/health"; Allow401 = $false },
    @{ Name = "Admin API (v1/stats)";  Url = "http://localhost:8004/api/v1/stats"; Allow401 = $true },
    @{ Name = "Dashboard (via nginx)"; Url = "http://localhost:3000/api/v1/health"; Allow401 = $false }
)

$failed = 0
foreach ($c in $checks) {
    $code = if ($c.Allow401) { Test-Url -Uri $c.Url -TimeoutSec 10 -ReturnCodeOnError } else { Test-Url -Uri $c.Url -TimeoutSec 10 }
    $ok = ($code -eq 200) -or ($c.Allow401 -and $code -eq 401)
    $status = if ($ok) { "OK" } else { Get-Status -Code $code }
    $color = if ($ok) { "Green" } else { "Red" }
    if (-not $ok) { $failed++ }
    Write-Host "  $($c.Name): " -NoNewline
    Write-Host $status -ForegroundColor $color -NoNewline
    Write-Host " ($($c.Url))"
}

Write-Host ""
if ($failed -gt 0) {
    Write-Host "Result: $failed check(s) failed. Fix admin-api dependency URLs and ensure services are on homeiq-network." -ForegroundColor Red
    Pop-Location
    exit 1
}
Write-Host "Result: All core stack checks passed. Dashboard should show healthy/degraded (not 502)." -ForegroundColor Green
Pop-Location
exit 0
