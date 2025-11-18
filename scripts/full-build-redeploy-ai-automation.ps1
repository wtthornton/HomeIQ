# Full Build and Redeploy AI Automation Services
# This script performs a complete rebuild and restart of all AI automation services

Write-Host "🚀 Full Build and Redeploy - AI Automation Services" -ForegroundColor Green
Write-Host "=====================================================" -ForegroundColor Green
Write-Host ""

$ErrorActionPreference = "Continue"

# Step 1: Clear all caches
Write-Host "🧹 Step 1: Clearing all caches..." -ForegroundColor Cyan

# Frontend caches
$uiPath = "services\ai-automation-ui"
$cachePaths = @(
    "$uiPath\node_modules\.vite",
    "$uiPath\dist",
    "$uiPath\.vite",
    "$uiPath\.next"
)

foreach ($path in $cachePaths) {
    if (Test-Path $path) {
        Remove-Item -Recurse -Force $path -ErrorAction SilentlyContinue
        Write-Host "   ✅ Cleared: $path" -ForegroundColor Green
    }
}

# Backend Python caches
$servicePath = "services\ai-automation-service"
Get-ChildItem -Path $servicePath -Recurse -Include "__pycache__", "*.pyc" -ErrorAction SilentlyContinue | 
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "   ✅ Cleared Python __pycache__ directories" -ForegroundColor Green

# Step 2: Stop running services
Write-Host ""
Write-Host "🛑 Step 2: Stopping running services..." -ForegroundColor Cyan

# Find and stop Node processes for frontend
$nodeProcesses = Get-Process node -ErrorAction SilentlyContinue | 
    Where-Object { $_.Path -like "*ai-automation-ui*" -or $_.CommandLine -like "*vite*" -or $_.CommandLine -like "*3001*" }
if ($nodeProcesses) {
    $nodeProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "   ✅ Stopped frontend Node processes" -ForegroundColor Green
} else {
    Write-Host "   ℹ️  No frontend processes found running" -ForegroundColor Yellow
}

# Find and stop Python processes for backend
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue | 
    Where-Object { $_.CommandLine -like "*uvicorn*" -and $_.CommandLine -like "*ai-automation*" }
if ($pythonProcesses) {
    $pythonProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "   ✅ Stopped backend Python processes" -ForegroundColor Green
} else {
    Write-Host "   ℹ️  No backend processes found running" -ForegroundColor Yellow
}

# Step 3: Rebuild frontend
Write-Host ""
Write-Host "🔨 Step 3: Rebuilding frontend..." -ForegroundColor Cyan
Push-Location $uiPath
try {
    Write-Host "   Installing dependencies..." -ForegroundColor Yellow
    npm install --no-audit 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Dependencies installed" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Warning: npm install had issues" -ForegroundColor Yellow
    }
    
    Write-Host "   Building production bundle..." -ForegroundColor Yellow
    npm run build 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Frontend build complete" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Warning: Build had issues, but continuing..." -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ❌ Error during frontend build: $_" -ForegroundColor Red
} finally {
    Pop-Location
}

# Step 4: Verify backend code
Write-Host ""
Write-Host "🔍 Step 4: Verifying backend code..." -ForegroundColor Cyan
Push-Location $servicePath
try {
    # Check if main entry point exists
    $mainFile = "src\main.py"
    if (Test-Path $mainFile) {
        Write-Host "   ✅ Backend entry point found: $mainFile" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Warning: Backend entry point not found at $mainFile" -ForegroundColor Yellow
    }
    
    # Check if ask_ai_router exists
    $routerFile = "src\api\ask_ai_router.py"
    if (Test-Path $routerFile) {
        Write-Host "   ✅ Router file found: $routerFile" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Warning: Router file not found at $routerFile" -ForegroundColor Yellow
    }
} finally {
    Pop-Location
}

# Step 5: Start services
Write-Host ""
Write-Host "🚀 Step 5: Starting services..." -ForegroundColor Cyan
Write-Host ""
Write-Host "   📋 Manual start required - run these commands in separate terminals:" -ForegroundColor Yellow
Write-Host ""
Write-Host "   Backend (Terminal 1):" -ForegroundColor White
Write-Host "     cd services\ai-automation-service" -ForegroundColor Gray
Write-Host "     python -m uvicorn src.main:app --host 0.0.0.0 --port 8018 --reload" -ForegroundColor Gray
Write-Host ""
Write-Host "   Frontend (Terminal 2):" -ForegroundColor White
Write-Host "     cd services\ai-automation-ui" -ForegroundColor Gray
Write-Host "     npm run dev" -ForegroundColor Gray
Write-Host ""

# Step 6: Final instructions
Write-Host "📋 Step 6: After starting services..." -ForegroundColor Cyan
Write-Host ""
Write-Host "   1. Clear browser cache:" -ForegroundColor White
Write-Host "      - Press Ctrl+Shift+Delete" -ForegroundColor Gray
Write-Host "      - Or hard refresh: Ctrl+F5" -ForegroundColor Gray
Write-Host "      - Or DevTools (F12) > Network > Check 'Disable cache'" -ForegroundColor Gray
Write-Host ""
Write-Host "   2. Navigate to: http://localhost:3001/ask-ai" -ForegroundColor White
Write-Host ""
Write-Host "   3. Open browser console (F12) to see debug logs" -ForegroundColor White
Write-Host ""
Write-Host "   4. Test the flow:" -ForegroundColor White
Write-Host "      - Ask a question that triggers clarification" -ForegroundColor Gray
Write-Host "      - Answer the questions" -ForegroundColor Gray
Write-Host "      - Check console for confidence improvement logs" -ForegroundColor Gray
Write-Host "      - Verify enhancements appear in UI" -ForegroundColor Gray
Write-Host ""

Write-Host "✅ Full build and redeploy preparation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "💡 Tip: Keep the browser console open to see debug logs" -ForegroundColor Yellow
Write-Host "   that will help identify if confidence data is being received." -ForegroundColor Yellow


