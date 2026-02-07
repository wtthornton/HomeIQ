# Docker E2E Test Runner for HA Ingestor (PowerShell)
# This script runs comprehensive end-to-end tests against the Docker deployment

param(
    [switch]$CrossBrowser,
    [switch]$Mobile,
    [switch]$Debug
)

# Configuration
$DockerComposeFile = "docker-compose.yml"
$TestResultsDir = "test-results"
$ReportsDir = "test-reports"

Write-Host "🚀 HA Ingestor Docker E2E Test Runner" -ForegroundColor Blue
Write-Host "==================================" -ForegroundColor Blue

# Function to print status messages
function Write-Status {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Cyan

# Check if Docker is running
try {
    docker ps | Out-Null
    Write-Status "Docker is running"
} catch {
    Write-Error "Docker is not running. Please start Docker first."
    exit 1
}

# Check if Docker Compose is available
try {
    docker-compose --version | Out-Null
    Write-Status "Docker Compose is available"
} catch {
    Write-Error "Docker Compose is not installed or not in PATH."
    exit 1
}

# Check if the HA Ingestor deployment exists
if (-not (Test-Path $DockerComposeFile)) {
    Write-Error "Docker Compose file not found: $DockerComposeFile"
    exit 1
}
Write-Status "Docker Compose file found"

# Check if required containers are running
Write-Host "Checking Docker containers..." -ForegroundColor Cyan
# Epic 31: enrichment-pipeline deprecated, admin-api on 8004
$RequiredContainers = @(
    "homeiq-influxdb",
    "homeiq-websocket",
    "homeiq-admin",
    "homeiq-dashboard"
)

foreach ($container in $RequiredContainers) {
    $runningContainers = docker ps --format "{{.Names}}"
    if ($runningContainers -contains $container) {
        Write-Status "$container is running"
    } else {
        Write-Error "$container is not running"
        Write-Host "Please start the HA Ingestor deployment first:" -ForegroundColor Yellow
        Write-Host "  docker-compose up -d" -ForegroundColor Yellow
        exit 1
    }
}

# Wait for services to be healthy
Write-Host "Waiting for services to be healthy..." -ForegroundColor Cyan
Start-Sleep -Seconds 10

# Check service health endpoints
$Services = @(
    @{Name="InfluxDB"; Url="http://localhost:8086/health"},
    @{Name="WebSocket"; Url="http://localhost:8001/health"},
    @{Name="Data API"; Url="http://localhost:8006/health"},
    @{Name="Admin API"; Url="http://localhost:8004/api/v1/health"},
    @{Name="Dashboard"; Url="http://localhost:3000"}
)

foreach ($service in $Services) {
    try {
        $response = Invoke-WebRequest -Uri $service.Url -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Status "$($service.Name) is healthy"
        }
    } catch {
        Write-Warning "$($service.Name) health check failed (this might be normal during startup)"
    }
}

# Create test results directory
if (-not (Test-Path $TestResultsDir)) {
    New-Item -ItemType Directory -Path $TestResultsDir | Out-Null
}
if (-not (Test-Path $ReportsDir)) {
    New-Item -ItemType Directory -Path $ReportsDir | Out-Null
}

Write-Host ""
Write-Host "Running E2E Tests..." -ForegroundColor Cyan
Write-Host "===================" -ForegroundColor Cyan

# Install Playwright browsers if not already installed
Write-Host "Ensuring Playwright browsers are installed..." -ForegroundColor Cyan
npx playwright install --with-deps

# Run different test suites
Write-Host ""
Write-Host "1. System Health Tests" -ForegroundColor Cyan
Write-Host "----------------------" -ForegroundColor Cyan
npx playwright test tests/e2e/system-health.spec.ts --config=tests/e2e/docker-deployment.config.ts --project=docker-chromium --reporter=html,json,junit

Write-Host ""
Write-Host "2. Dashboard Functionality Tests" -ForegroundColor Cyan
Write-Host "--------------------------------" -ForegroundColor Cyan
npx playwright test tests/e2e/dashboard-functionality.spec.ts --config=tests/e2e/docker-deployment.config.ts --project=docker-chromium --reporter=html,json,junit

Write-Host ""
Write-Host "3. Monitoring Screen Tests" -ForegroundColor Cyan
Write-Host "--------------------------" -ForegroundColor Cyan
npx playwright test tests/e2e/monitoring-screen.spec.ts --config=tests/e2e/docker-deployment.config.ts --project=docker-chromium --reporter=html,json,junit

Write-Host ""
Write-Host "4. Settings Screen Tests" -ForegroundColor Cyan
Write-Host "------------------------" -ForegroundColor Cyan
npx playwright test tests/e2e/settings-screen.spec.ts --config=tests/e2e/docker-deployment.config.ts --project=docker-chromium --reporter=html,json,junit

Write-Host ""
Write-Host "5. Visual Regression Tests" -ForegroundColor Cyan
Write-Host "--------------------------" -ForegroundColor Cyan
npx playwright test tests/e2e/visual-regression.spec.ts --config=tests/e2e/docker-deployment.config.ts --project=docker-chromium --reporter=html,json,junit

Write-Host ""
Write-Host "6. Integration Tests" -ForegroundColor Cyan
Write-Host "--------------------" -ForegroundColor Cyan
npx playwright test tests/e2e/integration.spec.ts --config=tests/e2e/docker-deployment.config.ts --project=docker-chromium --reporter=html,json,junit

Write-Host ""
Write-Host "7. Performance Tests" -ForegroundColor Cyan
Write-Host "--------------------" -ForegroundColor Cyan
npx playwright test tests/e2e/performance.spec.ts --config=tests/e2e/docker-deployment.config.ts --project=docker-chromium --reporter=html,json,junit

# Run cross-browser tests (optional)
if ($CrossBrowser) {
    Write-Host ""
    Write-Host "8. Cross-Browser Tests" -ForegroundColor Cyan
    Write-Host "----------------------" -ForegroundColor Cyan
    npx playwright test --config=tests/e2e/docker-deployment.config.ts --project=docker-firefox,docker-webkit --reporter=html,json,junit
}

# Run mobile tests (optional)
if ($Mobile) {
    Write-Host ""
    Write-Host "9. Mobile Tests" -ForegroundColor Cyan
    Write-Host "---------------" -ForegroundColor Cyan
    npx playwright test --config=tests/e2e/docker-deployment.config.ts --project=docker-mobile-chrome,docker-mobile-safari --reporter=html,json,junit
}

# Generate comprehensive report
Write-Host ""
Write-Host "Generating Test Reports..." -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan

# Copy test results to reports directory
if (Test-Path $TestResultsDir) {
    Copy-Item -Path "$TestResultsDir\*" -Destination $ReportsDir -Recurse -Force
}

# Generate summary report
$SummaryContent = @"
# HA Ingestor E2E Test Summary

## Test Execution Details
- **Date**: $(Get-Date)
- **Docker Compose File**: $DockerComposeFile
- **Test Configuration**: docker-deployment.config.ts

## Test Suites Executed
1. ✅ System Health Tests
2. ✅ Dashboard Functionality Tests
3. ✅ Monitoring Screen Tests
4. ✅ Settings Screen Tests
5. ✅ Visual Regression Tests
6. ✅ Integration Tests
7. ✅ Performance Tests

## Test Results
- **Results Directory**: $TestResultsDir
- **HTML Report**: $ReportsDir\html-report\index.html
- **JSON Results**: $TestResultsDir\results.json
- **JUnit Results**: $TestResultsDir\results.xml

## Docker Environment
- **InfluxDB**: http://localhost:8086
- **WebSocket Ingestion**: http://localhost:8001
- **Enrichment Pipeline**: http://localhost:8002
- **Admin API**: http://localhost:8004
- **Health Dashboard**: http://localhost:3000
- **Data Retention**: http://localhost:8080

## Next Steps
1. Review the HTML report for detailed test results
2. Check failed tests and investigate issues
3. Update baseline screenshots if visual regression tests fail
4. Optimize performance if performance tests fail
"@

$SummaryContent | Out-File -FilePath "$ReportsDir\test-summary.md" -Encoding UTF8

Write-Status "Test execution completed"
Write-Status "Results saved to: $ReportsDir\"
Write-Status "HTML report: $ReportsDir\html-report\index.html"

Write-Host ""
Write-Host "🎉 E2E Testing Complete!" -ForegroundColor Green
Write-Host "=======================" -ForegroundColor Green
Write-Host ""
Write-Host "To view the test results:" -ForegroundColor Yellow
Write-Host "  start $ReportsDir\html-report\index.html" -ForegroundColor White
Write-Host ""
Write-Host "To run specific test suites:" -ForegroundColor Yellow
Write-Host "  npx playwright test tests/e2e/system-health.spec.ts --config=tests/e2e/docker-deployment.config.ts" -ForegroundColor White
Write-Host ""
Write-Host "To run with different options:" -ForegroundColor Yellow
Write-Host "  .\tests\e2e\run-docker-tests.ps1 -CrossBrowser  # Include cross-browser tests" -ForegroundColor White
Write-Host "  .\tests\e2e\run-docker-tests.ps1 -Mobile       # Include mobile tests" -ForegroundColor White
