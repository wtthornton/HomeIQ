# Simple Smoke Tests for Blueprint-First Architecture

Write-Host "`n=== Smoke Test Results ===" -ForegroundColor Yellow

# Test 1: Blueprint Index Health
Write-Host "`n1. Blueprint Index Service:" -ForegroundColor Cyan
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8038/health"
    Write-Host "   [PASS] Health: $($r.status)" -ForegroundColor Green
} catch {
    Write-Host "   [FAIL] Health check: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: Blueprint Index Root
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8038/"
    Write-Host "   [PASS] Root endpoint: $($r.service)" -ForegroundColor Green
} catch {
    Write-Host "   [FAIL] Root endpoint: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: AI Pattern Service Health
Write-Host "`n2. AI Pattern Service:" -ForegroundColor Cyan
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8034/health"
    Write-Host "   [PASS] Health: $($r.status)" -ForegroundColor Green
} catch {
    Write-Host "   [FAIL] Health check: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: Blueprint Opportunities
Write-Host "`n3. Blueprint Opportunities Endpoint:" -ForegroundColor Cyan
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8034/api/v1/blueprint-opportunities?limit=3"
    Write-Host "   [PASS] Endpoint accessible" -ForegroundColor Green
    Write-Host "   Success: $($r.success)" -ForegroundColor Gray
    Write-Host "   Opportunities: $($r.data.opportunities.Count)" -ForegroundColor Gray
} catch {
    Write-Host "   [FAIL] Endpoint error: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 5: Synergies Endpoint
Write-Host "`n4. Synergies Endpoint:" -ForegroundColor Cyan
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8034/api/v1/synergies/list?limit=3"
    Write-Host "   [PASS] Endpoint accessible" -ForegroundColor Green
    Write-Host "   Success: $($r.success)" -ForegroundColor Gray
} catch {
    Write-Host "   [FAIL] Endpoint error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== Tests Complete ===" -ForegroundColor Yellow
