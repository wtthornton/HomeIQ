# start-stack.ps1 — Start all 9 HomeIQ domains in dependency order.
# Each domain launches as a separate Docker Desktop group (via compose name: directive).
# Uses --profile production so data-collectors includes air-quality, carbon-intensity, etc.
#
# Usage:
#   .\scripts\start-stack.ps1              # Full startup with health polling
#   .\scripts\start-stack.ps1 -SkipWait    # Skip health polling after core-platform

param(
    [switch]$SkipWait
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

$Domains = @(
    "core-platform"
    "data-collectors"
    "ml-engine"
    "automation-core"
    "blueprints"
    "energy-analytics"
    "device-management"
    "pattern-analysis"
    "frontends"
)

function Wait-ForHealth {
    param(
        [string]$Url,
        [string]$Label,
        [int]$Timeout = 60,
        [int]$Interval = 5
    )

    $elapsed = 0
    while ($elapsed -lt $Timeout) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Host "[OK] $Label is healthy" -ForegroundColor Green
                return $true
            }
        } catch {
            # Service not ready yet
        }
        Write-Host "[WAITING] $Label not ready yet (${elapsed}s / ${Timeout}s)..." -ForegroundColor Yellow
        Start-Sleep -Seconds $Interval
        $elapsed += $Interval
    }

    Write-Host "[TIMEOUT] $Label did not become healthy within ${Timeout}s" -ForegroundColor Red
    return $false
}

function Start-Domain {
    param([string]$DomainName)

    $composeFile = Join-Path -Path $ProjectRoot -ChildPath "domains\$DomainName\compose.yml"
    if (-not (Test-Path $composeFile)) {
        Write-Host "[ERROR] Compose file not found: $composeFile" -ForegroundColor Red
        return
    }

    Write-Host "[INFO] Starting $DomainName..." -ForegroundColor Cyan
    & docker compose -f $composeFile --profile production up -d --pull always --force-recreate
    Write-Host "[OK] $DomainName started." -ForegroundColor Green
}

# Ensure the shared Docker network exists
Write-Host "[INFO] Ensuring homeiq-network exists..." -ForegroundColor Cyan
& "$ScriptDir\ensure-network.ps1"
Write-Host ""

# 1. core-platform (critical)
Start-Domain -DomainName "core-platform"

if (-not $SkipWait) {
    Write-Host "[INFO] Waiting for core-platform dependencies..." -ForegroundColor Cyan
    Wait-ForHealth -Url "http://localhost:8086/health" -Label "influxdb" | Out-Null
    Wait-ForHealth -Url "http://localhost:8006/health" -Label "data-api" | Out-Null
    Write-Host ""
}

# 2-9. Remaining domains
foreach ($domain in $Domains | Select-Object -Skip 1) {
    Start-Domain -DomainName $domain
}

# Summary
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "HomeIQ Full Stack Started" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
foreach ($domain in $Domains) {
    Write-Host "  * $domain" -ForegroundColor Green
}
Write-Host ""
Write-Host "Use '.\scripts\domain.ps1 status <domain>' to check individual domains."
Write-Host "Use '.\scripts\domain.ps1 logs <domain> [service]' to view logs."
Write-Host "=========================================="
