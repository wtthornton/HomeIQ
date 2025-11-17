# Quick restart script for AI Automation services
# This assumes services are running locally (not in Docker)

Write-Host "🔄 Restarting AI Automation Services" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green
Write-Host ""

# Check if frontend is running
$frontendProcess = Get-Process | Where-Object { $_.Path -like "*ai-automation-ui*" -or ($_.ProcessName -eq "node" -and $_.CommandLine -like "*vite*") }
if ($frontendProcess) {
    Write-Host "⚠️  Frontend dev server is running. Please stop it manually (Ctrl+C in its terminal)" -ForegroundColor Yellow
    Write-Host "   Then run: cd services\ai-automation-ui && npm run dev" -ForegroundColor Gray
} else {
    Write-Host "✅ Frontend is not running. Start it with:" -ForegroundColor Green
    Write-Host "   cd services\ai-automation-ui" -ForegroundColor Gray
    Write-Host "   npm run dev" -ForegroundColor Gray
}

Write-Host ""

# Check if backend is running
$backendProcess = Get-Process | Where-Object { $_.ProcessName -eq "python" -and $_.CommandLine -like "*uvicorn*" -and $_.CommandLine -like "*ai-automation*" }
if ($backendProcess) {
    Write-Host "⚠️  Backend service is running. Please stop it manually (Ctrl+C in its terminal)" -ForegroundColor Yellow
    Write-Host "   Then run: cd services\ai-automation-service && python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8007" -ForegroundColor Gray
} else {
    Write-Host "✅ Backend is not running. Start it with:" -ForegroundColor Green
    Write-Host "   cd services\ai-automation-service" -ForegroundColor Gray
    Write-Host "   python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8007" -ForegroundColor Gray
}

Write-Host ""
Write-Host "📋 After restarting:" -ForegroundColor Cyan
Write-Host "   1. Clear browser cache: Ctrl+Shift+Delete or hard refresh (Ctrl+F5)" -ForegroundColor White
Write-Host "   2. Open DevTools (F12) > Network tab > Check 'Disable cache'" -ForegroundColor White
Write-Host "   3. Navigate to http://localhost:3001/ask-ai" -ForegroundColor White
Write-Host ""

