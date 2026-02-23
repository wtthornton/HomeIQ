#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Comprehensive E2E Test Runner for HA Ingestor Dashboard
.DESCRIPTION
    Runs Playwright E2E tests with various options and provides helpful output
.PARAMETER Suite
    Test suite to run: full, services, all
.PARAMETER Browser
    Browser to use: chromium, firefox, webkit, all
.PARAMETER UI
    Run in UI mode (interactive)
.PARAMETER Headed
    Run with visible browser
.PARAMETER Debug
    Run in debug mode
.PARAMETER Report
    Show test report
.EXAMPLE
    .\run-tests.ps1 -Suite full
    .\run-tests.ps1 -Suite all -Browser chromium
    .\run-tests.ps1 -UI
#>

param(
    [Parameter(Position=0)]
    [ValidateSet("full", "services", "all", "quick")]
    [string]$Suite = "full",
    
    [ValidateSet("chromium", "firefox", "webkit", "all")]
    [string]$Browser = "chromium",
    
    [switch]$UI,
    [switch]$Headed,
    [switch]$Debug,
    [switch]$Report
)

# Colors
$Green = "`e[32m"
$Blue = "`e[34m"
$Yellow = "`e[33m"
$Red = "`e[31m"
$Reset = "`e[0m"

Write-Host ""
Write-Host "${Blue}╔════════════════════════════════════════════════════════╗${Reset}"
Write-Host "${Blue}║  HA Ingestor Dashboard - E2E Test Runner              ║${Reset}"
Write-Host "${Blue}╚════════════════════════════════════════════════════════╝${Reset}"
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "package.json")) {
    Write-Host "${Red}❌ Error: package.json not found${Reset}"
    Write-Host "${Yellow}Please run this script from the services/health-dashboard directory${Reset}"
    exit 1
}

# Check if node_modules exists
if (-not (Test-Path "node_modules")) {
    Write-Host "${Yellow}⚠️  node_modules not found. Running npm install...${Reset}"
    npm install
}

# Check if Playwright is installed
if (-not (Test-Path "node_modules/@playwright")) {
    Write-Host "${Yellow}⚠️  Playwright not found. Installing...${Reset}"
    npm install @playwright/test
    npx playwright install
}

# Check if backend services are running
Write-Host "${Blue}🔍 Checking backend services...${Reset}"
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000/api/health" -TimeoutSec 5 -UseBasicParsing
    Write-Host "${Green}✅ Backend services are running${Reset}"
    Write-Host "${Green}   Status: $($response.StatusCode)${Reset}"
} catch {
    Write-Host "${Red}❌ Backend services not responding${Reset}"
    Write-Host "${Yellow}   Please ensure the dashboard is running:${Reset}"
    Write-Host "${Yellow}   1. Start backend: docker-compose up -d${Reset}"
    Write-Host "${Yellow}   2. Start dashboard: npm run dev${Reset}"
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/N)"
    if ($continue -ne "y") {
        exit 1
    }
}

Write-Host ""

# Build test command
$testCmd = "npx playwright test"

# Show report if requested
if ($Report) {
    Write-Host "${Blue}📊 Opening test report...${Reset}"
    npx playwright show-report
    exit 0
}

# Add UI mode
if ($UI) {
    Write-Host "${Blue}🎮 Launching UI mode (interactive)...${Reset}"
    $testCmd += " --ui"
}

# Add headed mode
if ($Headed) {
    Write-Host "${Blue}👀 Running with visible browser...${Reset}"
    $testCmd += " --headed"
}

# Add debug mode
if ($Debug) {
    Write-Host "${Blue}🐛 Running in debug mode...${Reset}"
    $testCmd += " --debug"
}

# Add browser selection
if ($Browser -ne "all") {
    Write-Host "${Blue}🌐 Browser: $Browser${Reset}"
    $testCmd += " --project=$Browser"
} else {
    Write-Host "${Blue}🌐 Running on all browsers${Reset}"
}

# Add test suite selection
Write-Host "${Blue}📝 Test Suite: $Suite${Reset}"
switch ($Suite) {
    "full" {
        Write-Host "${Green}   Running comprehensive full dashboard tests${Reset}"
        $testCmd += " dashboard-full"
    }
    "services" {
        Write-Host "${Green}   Running services tab tests${Reset}"
        $testCmd += " services-tab"
    }
    "quick" {
        Write-Host "${Green}   Running quick smoke tests${Reset}"
        $testCmd += " --grep 'should load dashboard|should verify NO mock data'"
    }
    "all" {
        Write-Host "${Green}   Running all test suites${Reset}"
        # Run all tests
    }
}

Write-Host ""
Write-Host "${Blue}═══════════════════════════════════════════════════════${Reset}"
Write-Host "${Blue}  Starting Tests...${Reset}"
Write-Host "${Blue}═══════════════════════════════════════════════════════${Reset}"
Write-Host ""

# Run tests
$startTime = Get-Date
Invoke-Expression $testCmd
$exitCode = $LASTEXITCODE
$endTime = Get-Date
$duration = ($endTime - $startTime).TotalSeconds

Write-Host ""
Write-Host "${Blue}═══════════════════════════════════════════════════════${Reset}"

if ($exitCode -eq 0) {
    Write-Host "${Green}✅ All tests passed!${Reset}"
    Write-Host "${Green}   Duration: $([math]::Round($duration, 2))s${Reset}"
    Write-Host ""
    Write-Host "${Blue}📊 To view detailed report:${Reset}"
    Write-Host "${Yellow}   .\run-tests.ps1 -Report${Reset}"
} else {
    Write-Host "${Red}❌ Some tests failed${Reset}"
    Write-Host "${Red}   Duration: $([math]::Round($duration, 2))s${Reset}"
    Write-Host ""
    Write-Host "${Blue}📊 To view test results:${Reset}"
    Write-Host "${Yellow}   .\run-tests.ps1 -Report${Reset}"
    Write-Host ""
    Write-Host "${Blue}🐛 To debug:${Reset}"
    Write-Host "${Yellow}   .\run-tests.ps1 -Debug${Reset}"
}

Write-Host "${Blue}═══════════════════════════════════════════════════════${Reset}"
Write-Host ""

exit $exitCode

