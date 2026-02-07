# Home Assistant Ingestor - Smoke Test Execution Script
# This script runs comprehensive smoke tests to validate system health

param(
    [string]$AdminUrl = "http://localhost:8004",
    [switch]$Verbose,
    [switch]$JsonOutput,
    [int]$Timeout = 30
)

# Colors for output
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Blue"

# Function to print colored output
function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $Red
}

Write-Host "🧪 Home Assistant Ingestor - Smoke Test Suite" -ForegroundColor $Blue
Write-Host "=================================================" -ForegroundColor $Blue

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Status "Python detected: $pythonVersion"
} catch {
    Write-Error "Python not found! Please install Python to run smoke tests."
    exit 1
}

# Check if smoke test script exists
if (-not (Test-Path "tests/smoke_tests.py")) {
    Write-Error "Smoke test script not found: tests/smoke_tests.py"
    exit 1
}

# Build command arguments
$args = @("tests/smoke_tests.py")
$args += "--timeout", $Timeout

if ($Verbose) {
    $args += "--verbose"
}

if ($JsonOutput) {
    $args += "--output", "json"
}

# Run smoke tests
Write-Status "Running comprehensive smoke tests..."
Write-Status "Admin API (reference): $AdminUrl - smoke_tests.py tests all services directly"
Write-Status "Timeout: ${Timeout}s"

try {
    $result = python @args
    $exitCode = $LASTEXITCODE
    
    if ($JsonOutput) {
        # Output JSON results
        Write-Host $result
    } else {
        # Output console results
        Write-Host $result
    }
    
    if ($exitCode -eq 0) {
        Write-Success "🎉 All smoke tests passed! System is healthy and deployment ready."
        exit 0
    } else {
        Write-Error "❌ Smoke tests failed! System has issues that need attention."
        Write-Warning "Please review the test results above and fix critical issues."
        exit 1
    }
} catch {
    Write-Error "Failed to run smoke tests: $_"
    exit 1
}
