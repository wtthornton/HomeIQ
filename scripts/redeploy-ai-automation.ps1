# Redeploy AI Automation Service and UI with cache clearing
# This ensures all recent changes are deployed

Write-Host "🔄 Redeploying AI Automation Services with Cache Clearing" -ForegroundColor Green
Write-Host "=========================================================" -ForegroundColor Green
Write-Host ""

# Step 1: Clear frontend caches
Write-Host "🧹 Step 1: Clearing frontend caches..." -ForegroundColor Cyan
$uiPath = "services\ai-automation-ui"

if (Test-Path "$uiPath\node_modules\.vite") {
    Remove-Item -Recurse -Force "$uiPath\node_modules\.vite"
    Write-Host "   ✅ Cleared Vite cache" -ForegroundColor Green
}

if (Test-Path "$uiPath\dist") {
    Remove-Item -Recurse -Force "$uiPath\dist"
    Write-Host "   ✅ Cleared build output" -ForegroundColor Green
}

if (Test-Path "$uiPath\.vite") {
    Remove-Item -Recurse -Force "$uiPath\.vite"
    Write-Host "   ✅ Cleared .vite cache directory" -ForegroundColor Green
}

# Step 2: Clear Python cache for backend
Write-Host ""
Write-Host "🧹 Step 2: Clearing backend Python caches..." -ForegroundColor Cyan
$servicePath = "services\ai-automation-service"

Get-ChildItem -Path $servicePath -Recurse -Include "__pycache__", "*.pyc" | Remove-Item -Recurse -Force
Write-Host "   ✅ Cleared Python __pycache__ directories" -ForegroundColor Green

# Step 3: Rebuild frontend (if needed)
Write-Host ""
Write-Host "🔨 Step 3: Rebuilding frontend..." -ForegroundColor Cyan
Push-Location $uiPath
try {
    # Install dependencies to ensure everything is up to date
    Write-Host "   Installing/updating dependencies..." -ForegroundColor Yellow
    npm install
    
    Write-Host "   ✅ Frontend dependencies updated" -ForegroundColor Green
} catch {
    Write-Host "   ⚠️  Warning: npm install failed, continuing anyway..." -ForegroundColor Yellow
} finally {
    Pop-Location
}

# Step 4: Check if services are running in Docker
Write-Host ""
Write-Host "🐳 Step 4: Checking Docker services..." -ForegroundColor Cyan

$dockerComposeFiles = @("docker-compose.yml", "docker-compose.dev.yml")
$aiServiceRunning = $false

foreach ($file in $dockerComposeFiles) {
    if (Test-Path $file) {
        $services = docker-compose -f $file ps --services 2>$null
        if ($services -match "ai-automation") {
            $aiServiceRunning = $true
            Write-Host "   Found AI automation service in $file" -ForegroundColor Yellow
            
            Write-Host "   Rebuilding and restarting AI automation service..." -ForegroundColor Yellow
            docker-compose -f $file build --no-cache ai-automation-service 2>&1 | Out-Null
            docker-compose -f $file up -d --force-recreate ai-automation-service 2>&1 | Out-Null
            Write-Host "   ✅ AI automation service rebuilt and restarted" -ForegroundColor Green
            break
        }
    }
}

# Step 5: Instructions for manual restart
Write-Host ""
Write-Host "📋 Step 5: Manual steps required:" -ForegroundColor Cyan
Write-Host ""

if (-not $aiServiceRunning) {
    Write-Host "   The AI automation service doesn't appear to be in docker-compose." -ForegroundColor Yellow
    Write-Host "   Please restart it manually:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   Backend (AI Automation Service):" -ForegroundColor White
    Write-Host "     cd services\ai-automation-service" -ForegroundColor Gray
    Write-Host "     # Stop the current process (Ctrl+C if running in terminal)" -ForegroundColor Gray
    Write-Host "     # Then restart with: python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8007" -ForegroundColor Gray
    Write-Host ""
}

Write-Host "   Frontend (AI Automation UI):" -ForegroundColor White
Write-Host "     docker compose build ai-automation-ui" -ForegroundColor Gray
Write-Host "     docker compose up -d ai-automation-ui" -ForegroundColor Gray
Write-Host "     # Or restart: docker compose restart ai-automation-ui" -ForegroundColor Gray
Write-Host ""

Write-Host "   Browser Cache Clearing:" -ForegroundColor White
Write-Host "     - Press Ctrl+Shift+Delete to open clear cache dialog" -ForegroundColor Gray
Write-Host "     - Or do a hard refresh: Ctrl+F5 (Windows) or Cmd+Shift+R (Mac)" -ForegroundColor Gray
Write-Host "     - Or open DevTools (F12) > Network tab > Check 'Disable cache'" -ForegroundColor Gray
Write-Host ""

Write-Host "✅ Cache clearing complete!" -ForegroundColor Green
Write-Host ""
Write-Host "💡 Tip: After restarting, do a hard refresh (Ctrl+F5) in your browser" -ForegroundColor Yellow
Write-Host "   to ensure you're seeing the latest code changes." -ForegroundColor Yellow

