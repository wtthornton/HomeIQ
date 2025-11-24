# Deploy Phase 4.1 Enhancements - Complete Deployment Script
# This script rebuilds and restarts services with all Phase 4.1 changes

Write-Host "🚀 Deploying Phase 4.1 Enhancements" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green
Write-Host ""

# Step 1: Check current service status
Write-Host "📊 Step 1: Checking current service status..." -ForegroundColor Cyan
$status = docker compose ps ai-automation-service ai-automation-ui 2>&1
Write-Host $status
Write-Host ""

# Step 2: Clear Python cache for backend
Write-Host "🧹 Step 2: Clearing backend Python caches..." -ForegroundColor Cyan
$servicePath = "services\ai-automation-service"
if (Test-Path $servicePath) {
    Get-ChildItem -Path $servicePath -Recurse -Include "__pycache__", "*.pyc" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "   ✅ Cleared Python __pycache__ directories" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Service path not found, skipping cache clear" -ForegroundColor Yellow
}
Write-Host ""

# Step 3: Clear frontend build cache
Write-Host "🧹 Step 3: Clearing frontend build cache..." -ForegroundColor Cyan
$uiPath = "services\ai-automation-ui"
if (Test-Path "$uiPath\node_modules\.vite") {
    Remove-Item -Recurse -Force "$uiPath\node_modules\.vite" -ErrorAction SilentlyContinue
    Write-Host "   ✅ Cleared Vite cache" -ForegroundColor Green
}
if (Test-Path "$uiPath\dist") {
    Remove-Item -Recurse -Force "$uiPath\dist" -ErrorAction SilentlyContinue
    Write-Host "   ✅ Cleared build output" -ForegroundColor Green
}
Write-Host ""

# Step 4: Rebuild and restart backend service
Write-Host "🔨 Step 4: Rebuilding ai-automation-service..." -ForegroundColor Cyan
Write-Host "   This may take a few minutes..." -ForegroundColor Yellow
docker compose build ai-automation-service
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Backend service rebuilt successfully" -ForegroundColor Green
} else {
    Write-Host "   ❌ Backend rebuild failed!" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 5: Rebuild and restart frontend service
Write-Host "🔨 Step 5: Rebuilding ai-automation-ui..." -ForegroundColor Cyan
Write-Host "   This may take a few minutes..." -ForegroundColor Yellow
docker compose build ai-automation-ui
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Frontend service rebuilt successfully" -ForegroundColor Green
} else {
    Write-Host "   ❌ Frontend rebuild failed!" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 6: Restart services with new images
Write-Host "🔄 Step 6: Restarting services with new images..." -ForegroundColor Cyan
docker compose up -d --force-recreate ai-automation-service ai-automation-ui
if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Services restarted successfully" -ForegroundColor Green
} else {
    Write-Host "   ❌ Service restart failed!" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 7: Wait for services to be healthy
Write-Host "⏳ Step 7: Waiting for services to be healthy..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

# Step 8: Verify services are running
Write-Host "✅ Step 8: Verifying service status..." -ForegroundColor Cyan
$services = docker compose ps ai-automation-service ai-automation-ui --format json | ConvertFrom-Json
$backendRunning = $services | Where-Object { $_.Service -eq "ai-automation-service" -and $_.State -eq "running" }
$frontendRunning = $services | Where-Object { $_.Service -eq "ai-automation-ui" -and $_.State -eq "running" }

if ($backendRunning -and $frontendRunning) {
    Write-Host "   ✅ Both services are running" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Some services may not be running - check logs" -ForegroundColor Yellow
}
Write-Host ""

# Step 9: Display service URLs and next steps
Write-Host "🎉 Deployment Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Service URLs:" -ForegroundColor Cyan
Write-Host "   Backend API:  http://localhost:8024" -ForegroundColor White
Write-Host "   Frontend UI:  http://localhost:3001" -ForegroundColor White
Write-Host "   Suggestions:  http://localhost:3001/conversational" -ForegroundColor White
Write-Host ""
Write-Host "📋 Next Steps:" -ForegroundColor Cyan
Write-Host "   1. Check service logs:" -ForegroundColor White
Write-Host "      docker compose logs -f ai-automation-service ai-automation-ui" -ForegroundColor Gray
Write-Host ""
Write-Host "   2. Verify deployment:" -ForegroundColor White
Write-Host "      - Navigate to http://localhost:3001/conversational" -ForegroundColor Gray
Write-Host "      - Generate suggestions to test Phase 4.1 enhancements" -ForegroundColor Gray
Write-Host "      - Check for health badges and warnings in UI" -ForegroundColor Gray
Write-Host ""
Write-Host "   3. Monitor logs for errors:" -ForegroundColor White
Write-Host "      - Watch for 'HomeAssistantAutomationChecker initialized' message" -ForegroundColor Gray
Write-Host "      - Watch for health check and duplicate check messages" -ForegroundColor Gray
Write-Host ""
Write-Host "   4. Test Phase 4.1 features:" -ForegroundColor White
Write-Host "      - Attribute querying (check FeatureAnalyzer logs)" -ForegroundColor Gray
Write-Host "      - Health filtering (check for filtered suggestions)" -ForegroundColor Gray
Write-Host "      - Duplicate detection (check for duplicate filtering)" -ForegroundColor Gray
Write-Host ""
Write-Host "✅ Phase 4.1 Enhancements Deployed!" -ForegroundColor Green
Write-Host ""

