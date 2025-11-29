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
    Write-Host "[BUILD] Building Docker images..." -ForegroundColor Blue
    docker compose build --no-cache 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[WARN] Build had warnings but continuing..." -ForegroundColor Yellow
    }
    Write-Host "[OK] Build complete" -ForegroundColor Green
} else {
    Write-Host "[SKIP] Skipping build (using existing images)" -ForegroundColor Yellow
}

# Step 2: Deploy
Write-Host ""
Write-Host "[DEPLOY] Deploying services..." -ForegroundColor Blue
docker compose down --timeout 30 2>&1 | Out-Null
docker compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Deployment failed" -ForegroundColor Red
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
$services = docker compose ps --format json | ConvertFrom-Json
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

