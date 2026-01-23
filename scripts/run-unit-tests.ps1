# HomeIQ Unit Testing Framework
# PowerShell script to run all unit tests with coverage

param(
    [switch]$Verbose,
    [switch]$PythonOnly,
    [switch]$TypeScriptOnly,
    [switch]$CoverageOnly,
    [switch]$Help
)

# Show help if requested
if ($Help) {
    Write-Host "HomeIQ Unit Testing Framework" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\run-unit-tests.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Verbose        Verbose output"
    Write-Host "  -PythonOnly     Run only Python unit tests"
    Write-Host "  -TypeScriptOnly Run only TypeScript unit tests"
    Write-Host "  -CoverageOnly   Generate coverage reports only"
    Write-Host "  -Help           Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\run-unit-tests.ps1                    # Run all unit tests"
    Write-Host "  .\run-unit-tests.ps1 -Verbose           # Run with verbose output"
    Write-Host "  .\run-unit-tests.ps1 -PythonOnly        # Run only Python tests"
    Write-Host "  .\run-unit-tests.ps1 -TypeScriptOnly    # Run only TypeScript tests"
    exit 0
}

Write-Host "🧪 HomeIQ Unit Testing Framework" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

# Check if we're in the right directory
if (-not (Test-Path "scripts/run-unit-tests.py")) {
    Write-Host "❌ Error: Please run this script from the project root directory" -ForegroundColor Red
    Write-Host "   Current directory: $(Get-Location)" -ForegroundColor Red
    Write-Host "   Expected files: scripts/run-unit-tests.py" -ForegroundColor Red
    exit 1
}

# Check Python installation
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python not found"
    }
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Error: Python is not installed or not in PATH" -ForegroundColor Red
    exit 1
}

# Check Node.js installation (for TypeScript tests)
try {
    $nodeVersion = node --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Node.js not found"
    }
    Write-Host "✅ Node.js found: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Warning: Node.js not found, TypeScript tests will be skipped" -ForegroundColor Yellow
}

# Create test results directory
$testResultsDir = "test-results"
$pythonCoverageDir = "$testResultsDir/coverage/python"
$typescriptCoverageDir = "$testResultsDir/coverage/typescript"

if (-not (Test-Path $testResultsDir)) {
    New-Item -ItemType Directory -Path $testResultsDir -Force | Out-Null
}
if (-not (Test-Path $pythonCoverageDir)) {
    New-Item -ItemType Directory -Path $pythonCoverageDir -Force | Out-Null
}
if (-not (Test-Path $typescriptCoverageDir)) {
    New-Item -ItemType Directory -Path $typescriptCoverageDir -Force | Out-Null
}

Write-Host "📁 Created test results directories" -ForegroundColor Green
Write-Host ""

# Build command arguments
$args = @()

if ($Verbose) {
    $args += "--verbose"
}

if ($PythonOnly) {
    $args += "--python-only"
}

if ($TypeScriptOnly) {
    $args += "--typescript-only"
}

if ($CoverageOnly) {
    $args += "--coverage-only"
}

# Run the unit testing framework
Write-Host "🚀 Starting unit tests..." -ForegroundColor Cyan
Write-Host ""

try {
    if ($args.Count -gt 0) {
        & python scripts/run-unit-tests.py @args
    } else {
        & python scripts/run-unit-tests.py
    }
    
    $exitCode = $LASTEXITCODE
} catch {
    Write-Host "❌ Error running unit tests: $($_.Exception.Message)" -ForegroundColor Red
    $exitCode = 1
}

Write-Host ""
Write-Host "=================================" -ForegroundColor Cyan

if ($exitCode -eq 0) {
    Write-Host "🎉 All unit tests passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 Coverage reports available in:" -ForegroundColor Cyan
    Write-Host "   • test-results/coverage/python/     (Python coverage)" -ForegroundColor White
    Write-Host "   • test-results/coverage/typescript/  (TypeScript coverage)" -ForegroundColor White
    Write-Host "   • test-results/unit-test-report.html (Summary report)" -ForegroundColor White
} else {
    Write-Host "❌ Some unit tests failed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "📋 Check the detailed reports:" -ForegroundColor Cyan
    Write-Host "   • test-results/unit-test-results.json" -ForegroundColor White
    Write-Host "   • test-results/unit-test-report.html" -ForegroundColor White
}

exit $exitCode
