# Production Container Cleanup Script
# Removes test/dev containers and fixes production issues

Write-Host "=== Production Container Cleanup ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Identify test/dev containers
Write-Host "[1] Identifying test and development containers..." -ForegroundColor Blue
$testContainers = docker ps -a --format "{{.Names}}" | Where-Object { $_ -match "test|dev|simulator" -and $_ -notmatch "device|intelligence" }

if ($testContainers) {
    Write-Host "Found test/dev containers:" -ForegroundColor Yellow
    $testContainers | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
    
    Write-Host ""
    Write-Host "[2] Stopping and removing test/dev containers..." -ForegroundColor Blue
    $testContainers | ForEach-Object {
        Write-Host "  Removing: $_" -ForegroundColor Gray
        docker stop $_ 2>&1 | Out-Null
        docker rm $_ 2>&1 | Out-Null
    }
    Write-Host "[OK] Test/dev containers removed" -ForegroundColor Green
} else {
    Write-Host "[OK] No test/dev containers found" -ForegroundColor Green
}

# Step 2: Check for failing production services
Write-Host ""
Write-Host "[3] Checking production service status..." -ForegroundColor Blue
$failingServices = docker compose ps --format json | ConvertFrom-Json | Where-Object { 
    $_.State -eq "restarting" -or $_.State -eq "exited" -or $_.State -eq "dead"
}

if ($failingServices) {
    Write-Host "Found failing services:" -ForegroundColor Yellow
    $failingServices | ForEach-Object {
        Write-Host "  - $($_.Service): $($_.State) - $($_.Status)" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "[4] Stopping failing services..." -ForegroundColor Blue
    $failingServices | ForEach-Object {
        Write-Host "  Stopping: $($_.Service)" -ForegroundColor Gray
        docker compose stop $_.Service 2>&1 | Out-Null
    }
    Write-Host "[OK] Failing services stopped" -ForegroundColor Green
} else {
    Write-Host "[OK] No failing services found" -ForegroundColor Green
}

# Step 3: Show production services status
Write-Host ""
Write-Host "[5] Production services status:" -ForegroundColor Blue
$productionServices = docker compose ps --format json | ConvertFrom-Json | Where-Object { 
    $_.State -eq "running"
} | Sort-Object Service

$healthy = ($productionServices | Where-Object { $_.Health -eq "healthy" }).Count
$total = $productionServices.Count

Write-Host "  Running: $total services" -ForegroundColor Cyan
Write-Host "  Healthy: $healthy services" -ForegroundColor Cyan

Write-Host ""
Write-Host "=== Cleanup Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Review failing services and fix issues" -ForegroundColor White
Write-Host "  2. Restart production services: docker compose up -d" -ForegroundColor White
Write-Host "  3. Check logs: docker compose logs [service-name]" -ForegroundColor White

