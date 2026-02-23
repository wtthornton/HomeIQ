# E2E Testing Script for Services Tab
# Tests all three phases with Playwright

Write-Host "🚀 Services Tab E2E Testing Suite" -ForegroundColor Cyan
Write-Host "=" * 50

# Check if node_modules exists
if (-not (Test-Path "node_modules")) {
    Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
    npm install
}

# Check if Playwright browsers are installed
Write-Host "`n🌐 Checking Playwright browsers..." -ForegroundColor Yellow
$playwrightCheck = npx playwright --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing Playwright..." -ForegroundColor Yellow
    npm install -D @playwright/test
    npx playwright install
} else {
    Write-Host "✅ Playwright is ready" -ForegroundColor Green
}

# Build the dashboard
Write-Host "`n🔨 Building dashboard..." -ForegroundColor Yellow
npm run build

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Build successful" -ForegroundColor Green

# Run E2E tests
Write-Host "`n🧪 Running E2E tests..." -ForegroundColor Yellow
Write-Host "`nPhase 1: Service Cards & Monitoring" -ForegroundColor Cyan
Write-Host "Phase 2: Service Details Modal" -ForegroundColor Cyan
Write-Host "Phase 3: Dependencies Visualization`n" -ForegroundColor Cyan

# Run tests with Playwright
npx playwright test --reporter=html,list

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ All E2E tests passed!" -ForegroundColor Green
    Write-Host "`n📊 Test report generated: playwright-report/index.html" -ForegroundColor Cyan
    
    # Open report
    $openReport = Read-Host "`nOpen test report in browser? (y/n)"
    if ($openReport -eq 'y') {
        npx playwright show-report
    }
} else {
    Write-Host "`n❌ Some tests failed" -ForegroundColor Red
    Write-Host "Run 'npx playwright show-report' to view details" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n🎉 Testing complete!" -ForegroundColor Green

