# Complete deployment and testing script
# Deploys dashboard and runs comprehensive E2E tests

param(
    [switch]$SkipBuild,
    [switch]$Headless = $true,
    [string]$Browser = "chromium"
)

Write-Host "🚀 HA Ingestor Dashboard - Deploy & Test" -ForegroundColor Cyan
Write-Host "=" * 60

# Navigate to project root
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$dashboardPath = Split-Path -Parent $scriptPath
Set-Location $dashboardPath

# Step 1: Install dependencies
Write-Host "`n📦 Step 1: Checking dependencies..." -ForegroundColor Yellow
if (-not (Test-Path "node_modules") -or -not $SkipBuild) {
    Write-Host "Installing npm packages..." -ForegroundColor Yellow
    npm install
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "✅ Dependencies OK" -ForegroundColor Green
}

# Step 2: Build dashboard
if (-not $SkipBuild) {
    Write-Host "`n🔨 Step 2: Building dashboard..." -ForegroundColor Yellow
    npm run build
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Build failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Build successful" -ForegroundColor Green
} else {
    Write-Host "`n⏩ Step 2: Skipping build (--SkipBuild)" -ForegroundColor Yellow
}

# Step 3: Install Playwright
Write-Host "`n🌐 Step 3: Checking Playwright..." -ForegroundColor Yellow
$playwrightCheck = Get-Command "npx" -ErrorAction SilentlyContinue
if ($playwrightCheck) {
    npx playwright install --with-deps $Browser 2>&1 | Out-Null
    Write-Host "✅ Playwright ready" -ForegroundColor Green
} else {
    Write-Host "⚠️  Playwright check skipped" -ForegroundColor Yellow
}

# Step 4: Run E2E tests
Write-Host "`n🧪 Step 4: Running E2E Tests..." -ForegroundColor Yellow
Write-Host "`nTesting Phases:" -ForegroundColor Cyan
Write-Host "  Phase 1: Service Cards & Monitoring" -ForegroundColor White
Write-Host "  Phase 2: Service Details Modal" -ForegroundColor White
Write-Host "  Phase 3: Dependencies Visualization" -ForegroundColor White
Write-Host ""

$testArgs = @(
    "playwright", "test",
    "--project=$Browser",
    "--reporter=html,list"
)

if ($Headless) {
    Write-Host "Running in headless mode..." -ForegroundColor Gray
} else {
    $testArgs += "--headed"
    Write-Host "Running with browser UI..." -ForegroundColor Gray
}

npx @testArgs

$testResult = $LASTEXITCODE

# Step 5: Display results
Write-Host "`n" + ("=" * 60) -ForegroundColor Cyan
if ($testResult -eq 0) {
    Write-Host "✅ ALL TESTS PASSED!" -ForegroundColor Green
    Write-Host "`n📊 Test Summary:" -ForegroundColor Cyan
    Write-Host "  ✓ Phase 1: Service Cards - PASSED" -ForegroundColor Green
    Write-Host "  ✓ Phase 2: Service Details Modal - PASSED" -ForegroundColor Green
    Write-Host "  ✓ Phase 3: Dependencies Visualization - PASSED" -ForegroundColor Green
    
    Write-Host "`n📄 Test report: playwright-report/index.html" -ForegroundColor Cyan
    
    $openReport = Read-Host "`nOpen test report? (y/n)"
    if ($openReport -eq 'y') {
        npx playwright show-report
    }
    
    Write-Host "`n🎉 Deployment verified - Ready for production!" -ForegroundColor Green
} else {
    Write-Host "❌ SOME TESTS FAILED" -ForegroundColor Red
    Write-Host "`n📋 Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Review test report: npx playwright show-report" -ForegroundColor White
    Write-Host "  2. Check browser console for errors" -ForegroundColor White
    Write-Host "  3. Verify services are running: docker-compose ps" -ForegroundColor White
    
    exit 1
}

Write-Host "`n" + ("=" * 60) -ForegroundColor Cyan

