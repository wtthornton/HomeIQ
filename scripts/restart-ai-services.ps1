# Quick restart script for AI Automation services
# Services run in Docker containers

Write-Host "🔄 Restarting AI Automation Services" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green
Write-Host ""

Write-Host "📦 Restarting Docker containers..." -ForegroundColor Cyan
Write-Host ""

# Restart AI Automation services
Write-Host "Restarting ai-automation-service..." -ForegroundColor Yellow
docker compose restart ai-automation-service

Write-Host "Restarting ai-automation-ui..." -ForegroundColor Yellow
docker compose restart ai-automation-ui

Write-Host ""
Write-Host "✅ Services restarted!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Check service status: docker compose ps" -ForegroundColor White
Write-Host "   2. View logs: docker compose logs -f ai-automation-service ai-automation-ui" -ForegroundColor White
Write-Host "   3. Navigate to http://localhost:3001/ask-ai" -ForegroundColor White
Write-Host ""

