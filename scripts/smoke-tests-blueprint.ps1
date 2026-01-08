# Smoke Tests for Blueprint-First Architecture
# Tests blueprint-index and ai-pattern-service integration

$ErrorActionPreference = "Stop"
$testsPassed = 0
$testsFailed = 0
$testResults = @()

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [string]$Method = "GET",
        [object]$Body = $null,
        [int]$ExpectedStatus = 200
    )
    
    try {
        Write-Host "`n[TEST] $Name" -ForegroundColor Cyan
        Write-Host "  URL: $Url" -ForegroundColor Gray
        
        if ($Method -eq "GET") {
            $response = Invoke-RestMethod -Uri $Url -Method Get -ErrorAction Stop
        } else {
            $response = Invoke-RestMethod -Uri $Url -Method $Method -Body ($Body | ConvertTo-Json) -ContentType "application/json" -ErrorAction Stop
        }
        
        Write-Host "  ✓ Status: OK" -ForegroundColor Green
        Write-Host "  Response: $($response | ConvertTo-Json -Depth 2 -Compress)" -ForegroundColor Gray
        
        $script:testsPassed++
        $script:testResults += @{
            Test = $Name
            Status = "PASS"
            Details = "Status: $ExpectedStatus"
        }
        return $response
    }
    catch {
        Write-Host "  ✗ FAILED: $($_.Exception.Message)" -ForegroundColor Red
        $script:testsFailed++
        $script:testResults += @{
            Test = $Name
            Status = "FAIL"
            Details = $_.Exception.Message
        }
        return $null
    }
}

Write-Host "========================================" -ForegroundColor Yellow
Write-Host "Blueprint-First Architecture Smoke Tests" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow

# ============================================
# 1. Blueprint Index Service Tests
# ============================================
Write-Host "`n[SUITE] Blueprint Index Service Tests" -ForegroundColor Magenta

# Test 1.1: Health Check
Test-Endpoint -Name "Blueprint Index - Health Check" `
    -Url "http://localhost:8038/health"

# Test 1.2: Root Endpoint
Test-Endpoint -Name "Blueprint Index - Root Endpoint" `
    -Url "http://localhost:8038/"

# Test 1.3: Index Status
Test-Endpoint -Name "Blueprint Index - Status" `
    -Url "http://localhost:8038/api/blueprints/status"

# Test 1.4: Basic Search (should work even with empty index)
Test-Endpoint -Name "Blueprint Index - Basic Search" `
    -Url "http://localhost:8038/api/blueprints/search?limit=5"

# ============================================
# 2. AI Pattern Service Tests
# ============================================
Write-Host "`n[SUITE] AI Pattern Service Tests" -ForegroundColor Magenta

# Test 2.1: Health Check
Test-Endpoint -Name "AI Pattern Service - Health Check" `
    -Url "http://localhost:8034/health"

# Test 2.2: Root Endpoint
Test-Endpoint -Name "AI Pattern Service - Root Endpoint" `
    -Url "http://localhost:8034/"

# Test 2.3: Readiness Check
Test-Endpoint -Name "AI Pattern Service - Readiness" `
    -Url "http://localhost:8034/ready"

# Test 2.4: Liveness Check
Test-Endpoint -Name "AI Pattern Service - Liveness" `
    -Url "http://localhost:8034/live"

# ============================================
# 3. Blueprint Opportunity Endpoints (NEW)
# ============================================
Write-Host "`n[SUITE] Blueprint Opportunity Endpoints" -ForegroundColor Magenta

# Test 3.1: List Blueprint Opportunities
Test-Endpoint -Name "Blueprint Opportunities - List" `
    -Url "http://localhost:8034/api/v1/blueprint-opportunities?limit=10"

# Test 3.2: Blueprint Opportunities with Filters
$filteredUrl = 'http://localhost:8034/api/v1/blueprint-opportunities?min_fit_score=0.3&limit=5'
Test-Endpoint -Name "Blueprint Opportunities - Filtered" -Url $filteredUrl

# ============================================
# 4. Synergy Endpoints (Blueprint-Enriched)
# ============================================
Write-Host "`n[SUITE] Synergy Endpoints (Blueprint-Enriched)" -ForegroundColor Magenta

# Test 4.1: List Synergies (should include blueprint metadata)
Test-Endpoint -Name "Synergies - List" `
    -Url "http://localhost:8034/api/v1/synergies/list?limit=5"

# ============================================
# 5. Integration Tests
# ============================================
Write-Host "`n[SUITE] Integration Tests" -ForegroundColor Magenta

# Test 5.1: Verify ai-pattern-service can reach blueprint-index
# This is implicit in the blueprint opportunities endpoint working
Write-Host "`n[TEST] Service-to-Service Communication" -ForegroundColor Cyan
Write-Host "  Verifying ai-pattern-service can communicate with blueprint-index..." -ForegroundColor Gray

$blueprintOpps = Test-Endpoint -Name "Integration - Blueprint Opportunities" `
    -Url "http://localhost:8034/api/v1/blueprint-opportunities?limit=1"

if ($blueprintOpps -and $blueprintOpps.success) {
    Write-Host "  ✓ ai-pattern-service successfully queried blueprint-index" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Blueprint opportunities endpoint may not be fully integrated" -ForegroundColor Yellow
}

# ============================================
# Summary
# ============================================
Write-Host "`n========================================" -ForegroundColor Yellow
Write-Host "Test Summary" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "Tests Passed: $testsPassed" -ForegroundColor Green
Write-Host "Tests Failed: $testsFailed" -ForegroundColor $(if ($testsFailed -eq 0) { "Green" } else { "Red" })
Write-Host "Total Tests: $($testsPassed + $testsFailed)" -ForegroundColor Cyan

Write-Host "`nDetailed Results:" -ForegroundColor Yellow
$testResults | ForEach-Object {
    $color = if ($_.Status -eq "PASS") { "Green" } else { "Red" }
    Write-Host "  [$($_.Status)] $($_.Test)" -ForegroundColor $color
    if ($_.Status -eq "FAIL") {
        Write-Host "    → $($_.Details)" -ForegroundColor Red
    }
}

if ($testsFailed -eq 0) {
    Write-Host "`n✓ All smoke tests passed!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`n✗ Some smoke tests failed. Review the output above." -ForegroundColor Red
    exit 1
}
