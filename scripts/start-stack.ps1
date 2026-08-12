# start-stack.ps1 — Start all 9 HomeIQ domains in dependency order.
# Each domain launches as a separate Docker Desktop group (via compose name: directive).
# Uses --profile production so data-collectors includes air-quality, carbon-intensity, etc.
#
# Usage:
#   .\scripts\start-stack.ps1              # Full startup with health polling
#   .\scripts\start-stack.ps1 -SkipWait    # Skip health polling after core-platform
#   $env:STACK_REFRESH = "1"               # Opt in to --pull always --force-recreate

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

    $envFile = Join-Path -Path $ProjectRoot -ChildPath ".env"
    $envFileArgs = @()
    if (Test-Path $envFile) {
        $envFileArgs = @("--env-file", $envFile)
    }

    Write-Host "[INFO] Starting $DomainName..." -ForegroundColor Cyan
    # `--build` alone is enough to pick up source changes: the Dockerfiles COPY
    # specific paths, so BuildKit reuses every layer whose inputs are unchanged.
    # `--pull always` and `--force-recreate` are NOT defaults because they defeat
    # that caching. Set STACK_REFRESH=1 for the old behaviour when you genuinely
    # want fresh base images and clean containers. (Parity with start-stack.sh.)
    $refreshArgs = @()
    if ($env:STACK_REFRESH -eq "1") {
        $refreshArgs = @("--pull", "always", "--force-recreate")
    }
    & docker compose -f $composeFile @envFileArgs --profile production up -d --build @refreshArgs
    Write-Host "[OK] $DomainName started." -ForegroundColor Green
}

# Required env keys must exist BEFORE anything starts (TAP-5902): checks the
# manifest at env.required against .env by NAME only — values are never read
# into output. Parity with preflight-env.sh.
$manifest = Join-Path $ProjectRoot "env.required"
$envFile = Join-Path $ProjectRoot ".env"
if (-not (Test-Path $manifest)) {
    Write-Host "[ERROR] Env preflight failed - manifest not found: $manifest" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $envFile)) {
    Write-Host "[ERROR] Env preflight failed - .env not found (copy infrastructure/env.example)" -ForegroundColor Red
    exit 1
}
$envKeys = @{}
foreach ($line in Get-Content $envFile) {
    if ($line -match '^([A-Z_][A-Z0-9_]*)=(.+)$') { $envKeys[$Matches[1]] = $true }
}
$missing = @()
foreach ($row in Get-Content $manifest) {
    if ($row -match '^\s*(#|$)') { continue }
    $parts = $row -split "`t"
    if ($parts.Count -ge 2 -and $parts[1] -eq 'required' -and -not $envKeys.ContainsKey($parts[0])) {
        $missing += $parts[0]
    }
}
if ($missing.Count -gt 0) {
    Write-Host "[ERROR] Env preflight failed - REQUIRED keys absent or empty: $($missing -join ', ')" -ForegroundColor Red
    Write-Host "[ERROR] Restore them at key-name level - see docs/operations/env-restore.md" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Env preflight: all required keys present" -ForegroundColor Green

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
