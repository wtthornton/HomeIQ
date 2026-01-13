# Simple Smoke Tests
Write-Host "=== Smoke Tests ===" -ForegroundColor Cyan

# Test 1: Data-API Health
Write-Host "[1] data-api health..." -ForegroundColor Yellow
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8006/health"
    Write-Host "  PASSED - Status: $($r.status)" -ForegroundColor Green
} catch {
    Write-Host "  FAILED: $_" -ForegroundColor Red
}

# Test 2: Context Analysis
Write-Host "[2] Context analysis..." -ForegroundColor Yellow
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8031/api/v1/suggestions/debug/context"
    Write-Host "  PASSED" -ForegroundColor Green
    Write-Host "  Summary: $($r.summary.total_insights) insights" -ForegroundColor Gray
} catch {
    Write-Host "  FAILED: $_" -ForegroundColor Red
}

# Test 3: Carbon Intensity
Write-Host "[3] Carbon intensity endpoint..." -ForegroundColor Yellow
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8006/api/v1/energy/carbon-intensity/current"
    Write-Host "  PASSED - Data available" -ForegroundColor Green
} catch {
    if ($_.Exception.Response.StatusCode -eq 404) {
        Write-Host "  PASSED - 404 expected (no data)" -ForegroundColor Green
    } else {
        Write-Host "  FAILED: $_" -ForegroundColor Red
    }
}

Write-Host "=== Tests Complete ===" -ForegroundColor Cyan
