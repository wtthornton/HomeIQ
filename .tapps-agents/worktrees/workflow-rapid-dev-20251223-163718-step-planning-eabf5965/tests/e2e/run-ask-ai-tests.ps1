# Ask AI E2E Test Runner (PowerShell)
#
# Runs comprehensive E2E tests for Ask AI feature
# Tests query submission, test execution, approval workflow, and bug fixes

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Ask AI E2E Test Suite" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if services are running
Write-Host "📋 Checking service health..." -ForegroundColor Yellow

function Test-Service {
    param(
        [string]$Name,
        [string]$Url
    )
    
    try {
        $response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "✓ $Name is healthy" -ForegroundColor Green
            return $true
        }
    } catch {
        Write-Host "✗ $Name is not responding" -ForegroundColor Red
        return $false
    }
}

# Check AI Automation UI
if (-not (Test-Service "AI Automation UI" "http://localhost:3001")) {
    Write-Host "ERROR: AI Automation UI (port 3001) is not running" -ForegroundColor Red
    Write-Host "Start it with: docker-compose up -d ai-automation-ui"
    exit 1
}

# Check AI Automation Service
if (-not (Test-Service "AI Automation Service" "http://localhost:8018/health")) {
    Write-Host "WARNING: AI Automation Service (port 8018) is not responding" -ForegroundColor Yellow
    Write-Host "Some tests may fail. Start it with: docker-compose up -d ai-automation-service"
}

# Check Home Assistant (optional)
try {
    $haResponse = Invoke-WebRequest -Uri "http://192.168.1.86:8123/api/" -Method Get -TimeoutSec 3 -UseBasicParsing
    Write-Host "✓ Home Assistant is reachable" -ForegroundColor Green
} catch {
    Write-Host "⚠  Home Assistant is not reachable (test automations won't execute)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Running Ask AI E2E Tests" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Change to test directory
Set-Location -Path "$PSScriptRoot"

# Install dependencies if needed
if (-not (Test-Path "node_modules")) {
    Write-Host "📦 Installing test dependencies..." -ForegroundColor Yellow
    npm install
}

# Run tests
Write-Host "🧪 Running tests..." -ForegroundColor Yellow
Write-Host ""

# Default: Run all Ask AI tests
$TestFile = if ($args.Count -gt 0) { $args[0] } else { "ask-ai-complete.spec.ts" }

$playwrightArgs = @(
    "playwright", "test", $TestFile,
    "--reporter=html",
    "--reporter=list",
    "--output=test-results/ask-ai"
)

# Add any additional arguments
if ($args.Count -gt 1) {
    $playwrightArgs += $args[1..($args.Count-1)]
}

npx @playwrightArgs

$TestExitCode = $LASTEXITCODE

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Test Results" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($TestExitCode -eq 0) {
    Write-Host "✅ All tests passed!" -ForegroundColor Green
} else {
    Write-Host "❌ Some tests failed" -ForegroundColor Red
}

Write-Host ""
Write-Host "📊 View detailed results:"
Write-Host "   npx playwright show-report"
Write-Host ""
Write-Host "🎥 Screenshots and videos (on failure):"
Write-Host "   test-results/ask-ai/"
Write-Host ""

exit $TestExitCode

