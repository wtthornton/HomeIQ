# Deploy Home Type Integration Changes (PowerShell)
# This script rebuilds and restarts the services with home type integration

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Home Type Integration Deployment" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Services to rebuild
$Services = @("ai-automation-service", "data-api", "websocket-ingestion")

Write-Host "Step 1: Rebuilding Docker containers..." -ForegroundColor Yellow
Write-Host ""

foreach ($service in $Services) {
    Write-Host "  → Rebuilding $service..." -ForegroundColor Gray
    docker-compose build $service
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    ✅ $service rebuilt successfully" -ForegroundColor Green
    } else {
        Write-Host "    ❌ Failed to rebuild $service" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Step 2: Restarting services..." -ForegroundColor Yellow
Write-Host ""

foreach ($service in $Services) {
    Write-Host "  → Restarting $service..." -ForegroundColor Gray
    docker-compose up -d $service
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    ✅ $service restarted successfully" -ForegroundColor Green
    } else {
        Write-Host "    ❌ Failed to restart $service" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Step 3: Waiting for services to be healthy..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host ""
Write-Host "Step 4: Verifying service health..." -ForegroundColor Yellow
Write-Host ""

# Check services
foreach ($service in $Services) {
    $status = docker-compose ps $service 2>&1
    if ($status -match "Up") {
        Write-Host "  ✅ $service is running" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $service is not running" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Check logs: docker-compose logs -f ai-automation-service"
Write-Host "  2. Verify home type client: Look for '✅ Home Type Client initialized'"
Write-Host "  3. Test endpoints:"
Write-Host "     - curl http://localhost:8018/api/home-type/classify?home_id=default"
Write-Host "     - curl http://localhost:8006/api/events/categories?hours=24"
Write-Host ""

