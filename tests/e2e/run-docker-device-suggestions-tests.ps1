# Run Device Suggestions Playwright Tests Against Docker Container
# 
# Prerequisites:
# 1. Docker containers must be running: ai-automation-ui, data-api, ha-ai-agent-service
# 2. Services must be healthy (check with: docker-compose ps)
# 3. API_KEY environment variable must be set
#
# Usage:
#   .\run-docker-device-suggestions-tests.ps1
#   .\run-docker-device-suggestions-tests.ps1 -Headed
#   .\run-docker-device-suggestions-tests.ps1 -Debug

param(
    [switch]$Headed,
    [switch]$Debug,
    [switch]$UI
)

# Set test environment
$env:TEST_BASE_URL = "http://localhost:3001"

# Check if API_KEY is set
if (-not $env:API_KEY) {
    Write-Host "⚠️  WARNING: API_KEY environment variable is not set" -ForegroundColor Yellow
    Write-Host "   Tests may fail if authentication is required" -ForegroundColor Yellow
}

# Check if services are running
Write-Host "🔍 Checking Docker services..." -ForegroundColor Cyan
$services = @("ai-automation-ui", "data-api", "ha-ai-agent-service")
$allRunning = $true

foreach ($service in $services) {
    $container = docker ps --filter "name=$service" --format "{{.Names}}" 2>$null
    if ($container) {
        Write-Host "  ✅ $service is running" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $service is NOT running" -ForegroundColor Red
        $allRunning = $false
    }
}

if (-not $allRunning) {
    Write-Host "`n⚠️  Some services are not running. Start them with:" -ForegroundColor Yellow
    Write-Host "   docker-compose up -d ai-automation-ui data-api ha-ai-agent-service" -ForegroundColor Yellow
    Write-Host "`nContinue anyway? (y/N): " -NoNewline -ForegroundColor Yellow
    $response = Read-Host
    if ($response -ne "y" -and $response -ne "Y") {
        exit 1
    }
}

# Test API connectivity
Write-Host "`n🔍 Testing API connectivity..." -ForegroundColor Cyan
try {
    $headers = @{}
    if ($env:API_KEY) {
        $headers["Authorization"] = "Bearer $env:API_KEY"
        $headers["X-HomeIQ-API-Key"] = $env:API_KEY
    }
    
    $response = Invoke-RestMethod -Uri "http://localhost:3001/api/data/devices?limit=1" -Headers $headers -ErrorAction Stop
    Write-Host "  ✅ API is accessible" -ForegroundColor Green
} catch {
    Write-Host "  ⚠️  API test failed: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "     Tests may still run, but some may fail" -ForegroundColor Yellow
}

# Change to test directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $scriptPath

# Build test command
$testFile = "ai-automation-ui/pages/device-suggestions.spec.ts"
$cmd = "npx playwright test $testFile --reporter=list"

if ($Headed) {
    $cmd += " --headed"
}

if ($Debug) {
    $cmd += " --debug"
}

if ($UI) {
    $cmd += " --ui"
}

Write-Host "`n🚀 Running Playwright tests..." -ForegroundColor Cyan
Write-Host "   Command: $cmd" -ForegroundColor Gray
Write-Host ""

# Run tests
Invoke-Expression $cmd
$exitCode = $LASTEXITCODE

Pop-Location

if ($exitCode -eq 0) {
    Write-Host "`n✅ All tests passed!" -ForegroundColor Green
} else {
    Write-Host "`n❌ Some tests failed. Exit code: $exitCode" -ForegroundColor Red
    Write-Host "`nView test report:" -ForegroundColor Yellow
    Write-Host "   npx playwright show-report" -ForegroundColor Gray
}

exit $exitCode
