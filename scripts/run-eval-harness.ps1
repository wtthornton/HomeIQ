# Evaluation Harness: Run 5 test prompts through the Ask AI pipeline
# and check for score regressions.
#
# Usage:
#   .\scripts\run-eval-harness.ps1                  # default threshold 10%
#   .\scripts\run-eval-harness.ps1 -Threshold 0.05  # stricter 5% threshold

param(
    [double]$Threshold = 0.10
)

$ErrorActionPreference = "Stop"

$prompts = @(
    "turn on the office lights",
    "set the thermostat to 72 degrees",
    "turn off all lights at midnight",
    "when I leave home turn off everything",
    "make it look like a party in the office"
)

$reportsDir = "tests/integration/reports"
if (-not (Test-Path $reportsDir)) {
    New-Item -ItemType Directory -Path $reportsDir -Force | Out-Null
}

Write-Host "Running evaluation harness ($($prompts.Count) prompts)..." -ForegroundColor Cyan

$failed = 0
foreach ($prompt in $prompts) {
    $slug = ($prompt -replace '\s+', '-').Substring(0, [Math]::Min(30, $prompt.Length))
    $outFile = "$reportsDir/eval-$slug.txt"

    Write-Host "  [$slug] " -NoNewline -ForegroundColor Yellow
    try {
        python tests/integration/test_ask_ai_pipeline.py $prompt -e -v -o $outFile
        Write-Host "OK" -ForegroundColor Green
    } catch {
        Write-Host "FAIL" -ForegroundColor Red
        $failed++
    }
}

Write-Host "`nChecking for regressions (threshold=$Threshold)..." -ForegroundColor Cyan
python tests/integration/eval_regression_check.py --threshold $Threshold

if ($LASTEXITCODE -ne 0) {
    Write-Host "`nRegression check FAILED" -ForegroundColor Red
    exit 1
}

if ($failed -gt 0) {
    Write-Host "`n$failed/$($prompts.Count) prompts failed" -ForegroundColor Red
    exit 1
}

Write-Host "`nAll prompts passed, no regressions detected" -ForegroundColor Green
