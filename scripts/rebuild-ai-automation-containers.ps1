# Rebuild AI Automation containers with latest code
# Run this after making code changes to ensure containers have the latest updates

Write-Host "🔨 Rebuilding AI Automation Containers" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Green
Write-Host ""

# Check if Docker is running
try {
    docker ps | Out-Null
    Write-Host "✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker Desktop is not running!" -ForegroundColor Red
    Write-Host "   Please start Docker Desktop and try again." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "📦 Checking for code changes..." -ForegroundColor Cyan

# Check last modified times
$uiFile = Get-Item "services\ai-automation-ui\src\components\ask-ai\DebugPanel.tsx" -ErrorAction SilentlyContinue
$serviceFile = Get-Item "services\ai-automation-service\src\api\ask_ai_router.py" -ErrorAction SilentlyContinue

if ($uiFile) {
    Write-Host "   UI: DebugPanel.tsx last modified: $($uiFile.LastWriteTime)" -ForegroundColor Gray
}
if ($serviceFile) {
    Write-Host "   Service: ask_ai_router.py last modified: $($serviceFile.LastWriteTime)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "🔨 Rebuilding containers..." -ForegroundColor Cyan
Write-Host ""

# Rebuild AI Automation Service
Write-Host "1. Rebuilding ai-automation-service..." -ForegroundColor Yellow
docker compose build ai-automation-service
if ($LASTEXITCODE -ne 0) {
    Write-Host "   ❌ Failed to build ai-automation-service" -ForegroundColor Red
    exit 1
}
Write-Host "   ✅ ai-automation-service built successfully" -ForegroundColor Green

Write-Host ""

# Rebuild AI Automation UI
Write-Host "2. Rebuilding ai-automation-ui..." -ForegroundColor Yellow
docker compose build ai-automation-ui
if ($LASTEXITCODE -ne 0) {
    Write-Host "   ❌ Failed to build ai-automation-ui" -ForegroundColor Red
    exit 1
}
Write-Host "   ✅ ai-automation-ui built successfully" -ForegroundColor Green

Write-Host ""
Write-Host "🚀 Restarting containers..." -ForegroundColor Cyan

# Restart containers
docker compose up -d ai-automation-service ai-automation-ui

if ($LASTEXITCODE -ne 0) {
    Write-Host "   ❌ Failed to start containers" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ Containers rebuilt and restarted!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Check container status: docker compose ps" -ForegroundColor White
Write-Host "   2. View logs: docker compose logs -f ai-automation-service ai-automation-ui" -ForegroundColor White
Write-Host "   3. Clear browser cache (Ctrl+Shift+Delete or Ctrl+F5)" -ForegroundColor White
Write-Host "   4. Navigate to http://localhost:3001/ask-ai" -ForegroundColor White
Write-Host ""

# Show container status
Write-Host "Container Status:" -ForegroundColor Cyan
docker compose ps ai-automation-service ai-automation-ui

