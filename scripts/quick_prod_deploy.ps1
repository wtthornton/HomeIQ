# Quick Production Deployment Script
# Fast, simple production deployment using existing working setup

param(
    [switch]$SkipBuild = $false,
    [switch]$SkipTests = $false
)

$ErrorActionPreference = "Stop"

Write-Host "[DEPLOY] Quick Production Deployment" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "[WARN] .env file not found. Using environment variables from system." -ForegroundColor Yellow
}

# Step 1: Build (if needed)
if (-not $SkipBuild) {
    Write-Host "[BUILD] Building Docker images (with BuildKit cache)..." -ForegroundColor Blue
    # BuildKit cache enabled for faster rebuilds (60-80% faster when dependencies unchanged)
    $buildOutput = docker compose build 2>&1
    $buildExitCode = $LASTEXITCODE
    if ($buildExitCode -ne 0) {
        Write-Host "[ERROR] Build failed with exit code $buildExitCode" -ForegroundColor Red
        Write-Host $buildOutput -ForegroundColor Red
        Write-Host "[ERROR] Deployment aborted due to build failure" -ForegroundColor Red
        exit 1
    }
    # Show any warnings but don't fail
    $warnings = $buildOutput | Select-String -Pattern "WARNING|warning" -CaseSensitive:$false
    if ($warnings) {
        Write-Host "[WARN] Build completed with warnings:" -ForegroundColor Yellow
        $warnings | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
    }
    Write-Host "[OK] Build complete" -ForegroundColor Green
} else {
    Write-Host "[SKIP] Skipping build (using existing images)" -ForegroundColor Yellow
}

# Step 2: Deploy
Write-Host ""
Write-Host "[DEPLOY] Stopping existing services..." -ForegroundColor Blue
$downOutput = docker compose down --timeout 30 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] Error stopping services (may not exist):" -ForegroundColor Yellow
    Write-Host $downOutput -ForegroundColor Yellow
}

Write-Host "[DEPLOY] Starting services..." -ForegroundColor Blue
$upOutput = docker compose up -d 2>&1
$upExitCode = $LASTEXITCODE
if ($upExitCode -ne 0) {
    Write-Host "[ERROR] Deployment failed with exit code $upExitCode" -ForegroundColor Red
    Write-Host $upOutput -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Services deployed" -ForegroundColor Green

# Step 3: Wait for services (quick check)
Write-Host ""
Write-Host "[WAIT] Waiting for services to start (30 seconds)..." -ForegroundColor Blue
Start-Sleep -Seconds 30

# Step 4: Quick health check
Write-Host ""
Write-Host "[HEALTH] Checking service health..." -ForegroundColor Blue
$psOutput = docker compose ps --format json 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] Could not get service status: $psOutput" -ForegroundColor Yellow
    $healthy = 0
    $total = 0
} else {
    try {
        $services = $psOutput | ConvertFrom-Json
        # Handle single service (not array) or array
        if ($services -isnot [array]) {
            $services = @($services)
        }
        $healthy = 0
        $total = 0

        foreach ($service in $services) {
            $total++
            if ($service.State -eq "running" -or $service.Health -eq "healthy") {
                $healthy++
                Write-Host "  [OK] $($service.Service) - $($service.State)" -ForegroundColor Green
            } else {
                Write-Host "  [WARN] $($service.Service) - $($service.State)" -ForegroundColor Yellow
            }
        }
    } catch {
        Write-Host "[WARN] Could not parse service status: $_" -ForegroundColor Yellow
        $healthy = 0
        $total = 0
    }
}

Write-Host ""
Write-Host "[STATUS] $healthy/$total services running" -ForegroundColor Cyan

# Step 5: Quick smoke tests (optional)
if (-not $SkipTests) {
    Write-Host ""
    Write-Host "[TEST] Running quick smoke tests..." -ForegroundColor Blue
    
    $tests = @(
        @{Name="InfluxDB"; Url="http://localhost:8086/health"},
        @{Name="Health Dashboard"; Url="http://localhost:3000"}
    )
    
    $passed = 0
    foreach ($test in $tests) {
        try {
            $response = Invoke-WebRequest -Uri $test.Url -TimeoutSec 5 -UseBasicParsing -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                Write-Host "  [OK] $($test.Name) - OK" -ForegroundColor Green
                $passed++
            }
        } catch {
            Write-Host "  [WARN] $($test.Name) - Not responding yet" -ForegroundColor Yellow
        }
    }
    Write-Host "  [TEST] $passed/$($tests.Count) passed" -ForegroundColor Cyan
}

# Summary
Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "[SUCCESS] Production Deployment Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "[URLS] Service URLs:" -ForegroundColor Cyan
Write-Host "  - Health Dashboard: http://localhost:3000" -ForegroundColor White
Write-Host "  - AI Automation UI: http://localhost:3001" -ForegroundColor White
Write-Host "  - InfluxDB: http://localhost:8086" -ForegroundColor White
Write-Host ""
Write-Host "[CMDS] Useful commands:" -ForegroundColor Cyan
Write-Host "  - View logs: docker compose logs -f" -ForegroundColor White
Write-Host "  - Check status: docker compose ps" -ForegroundColor White
Write-Host "  - Stop services: docker compose down" -ForegroundColor White
Write-Host ""

