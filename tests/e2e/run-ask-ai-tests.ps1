# Ask AI E2E Test Runner - Local Docker Stack
#
# Usage:
#   .\tests\e2e\run-ask-ai-tests.ps1              # Run all
#   .\tests\e2e\run-ask-ai-tests.ps1 -Complete     # Only ask-ai-complete
#   .\tests\e2e\run-ask-ai-tests.ps1 -Automation   # Only ask-ai-to-ha-automation
#   .\tests\e2e\run-ask-ai-tests.ps1 -Headed       # Headed browser
#   .\tests\e2e\run-ask-ai-tests.ps1 -UI           # Playwright UI mode

param(
    [switch]$Complete,
    [switch]$Automation,
    [switch]$Headed,
    [switch]$UI
)

$ErrorActionPreference = "Stop"

Write-Host "Ask AI E2E Tests - Local Docker Stack" -ForegroundColor Blue

# Pre-flight: check required services
$failed = $false
@(
    @{N="ai-automation-ui";      U="http://localhost:3001";        R=$true},
    @{N="ha-ai-agent-service";   U="http://localhost:8030/health"; R=$true},
    @{N="ai-automation-service"; U="http://localhost:8036/health"; R=$true}
) | ForEach-Object {
    try {
        Invoke-WebRequest -Uri $_.U -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop | Out-Null
        Write-Host "  [OK] $($_.N)" -ForegroundColor Green
    } catch {
        if ($_.R) { Write-Host "  [FAIL] $($_.N)" -ForegroundColor Red; $script:failed = $true }
        else      { Write-Host "  [WARN] $($_.N)" -ForegroundColor Yellow }
    }
}

if ($failed) {
    Write-Host "Required services not running. Start the stack first." -ForegroundColor Red
    exit 1
}

Write-Host ""

Push-Location tests/e2e
$testArgs = @("playwright", "test", "--config=ask-ai.config.ts")

if ($Complete)   { $testArgs += "ask-ai-complete.spec.ts" }
if ($Automation) { $testArgs += "ask-ai-to-ha-automation.spec.ts" }
if ($Headed)     { $testArgs += "--headed" }
if ($UI)         { $testArgs += "--ui" }

npx @testArgs
$exitCode = $LASTEXITCODE
Pop-Location

if ($exitCode -eq 0) { Write-Host "All tests passed!" -ForegroundColor Green }
else { Write-Host "Some tests failed. Run: npx playwright show-report test-results/ask-ai-html-report" -ForegroundColor Yellow }
exit $exitCode
