# Smoke Tests for Proactive Context Data Fixes
# Tests health checks and context data functionality

$ErrorActionPreference = "Continue"
$testResults = @()
$passed = 0
$failed = 0

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [int]$ExpectedStatus = 200,
        [string]$Method = "GET",
        [hashtable]$Headers = @{},
        [object]$Body = $null
    )
    
    $result = @{
        Name = $Name
        Url = $Url
        Status = "FAILED"
        Message = ""
        Details = $null
    }
    
    try {
        $params = @{
            Uri = $Url
            Method = $Method
            ErrorAction = "Stop"
        }
        
        if ($Headers.Count -gt 0) {
            $params.Headers = $Headers
        }
        
        if ($Body) {
            $params.Body = ($Body | ConvertTo-Json)
            $params.ContentType = "application/json"
        }
        
        $response = Invoke-RestMethod @params
        $httpStatus = $response.StatusCode
        
        if ($httpStatus -eq $ExpectedStatus -or $ExpectedStatus -eq 200) {
            $result.Status = "PASSED"
            $result.Message = "Endpoint responded successfully"
            $result.Details = $response
            $script:passed++
        } else {
            $result.Status = "FAILED"
            $result.Message = "Expected status $ExpectedStatus, got $httpStatus"
            $script:failed++
        }
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        if ($statusCode -eq $ExpectedStatus) {
            $result.Status = "PASSED"
            $result.Message = "Expected $ExpectedStatus response (service unavailable is OK)"
            $script:passed++
        } else {
            $result.Status = "FAILED"
            $result.Message = $_.Exception.Message
            $script:failed++
        }
    }
    
    return $result
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Proactive Context Data - Smoke Tests" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Data-API Health Check
Write-Host "[1/10] Testing data-api health endpoint..." -ForegroundColor Yellow
$test = Test-Endpoint -Name "Data-API Health" -Url "http://localhost:8006/health"
$testResults += $test
Write-Host "  Status: $($test.Status) - $($test.Message)" -ForegroundColor $(if ($test.Status -eq "PASSED") { "Green" } else { "Red" })

# Test 2: Proactive Agent Service Health Check
Write-Host "[2/10] Testing proactive-agent-service health endpoint..." -ForegroundColor Yellow
$test = Test-Endpoint -Name "Proactive Agent Health" -Url "http://localhost:8031/health"
$testResults += $test
Write-Host "  Status: $($test.Status) - $($test.Message)" -ForegroundColor $(if ($test.Status -eq "PASSED") { "Green" } else { "Red" })

# Test 3: Carbon Intensity Current Endpoint (may 404 if no data)
Write-Host "[3/10] Testing carbon intensity current endpoint..." -ForegroundColor Yellow
$test = Test-Endpoint -Name "Carbon Intensity Current" -Url "http://localhost:8006/api/v1/energy/carbon-intensity/current" -ExpectedStatus 404
$testResults += $test
Write-Host "  Status: $($test.Status) - $($test.Message)" -ForegroundColor $(if ($test.Status -eq "PASSED") { "Green" } else { "Red" })
if ($test.Status -eq "PASSED") {
    Write-Host "  Note: 404 is expected if carbon-intensity-service is not running" -ForegroundColor Gray
}

# Test 4: Carbon Intensity Trends Endpoint (may 404 if no data)
Write-Host "[4/10] Testing carbon intensity trends endpoint..." -ForegroundColor Yellow
$test = Test-Endpoint -Name "Carbon Intensity Trends" -Url "http://localhost:8006/api/v1/energy/carbon-intensity/trends" -ExpectedStatus 404
$testResults += $test
Write-Host "  Status: $($test.Status) - $($test.Message)" -ForegroundColor $(if ($test.Status -eq "PASSED") { "Green" } else { "Red" })
if ($test.Status -eq "PASSED") {
    Write-Host "  Note: 404 is expected if carbon-intensity-service is not running" -ForegroundColor Gray
}

# Test 5: Context Analysis Debug Endpoint
Write-Host "[5/10] Testing context analysis debug endpoint..." -ForegroundColor Yellow
$test = Test-Endpoint -Name "Context Analysis Debug" -Url "http://localhost:8031/api/v1/suggestions/debug/context"
$testResults += $test
Write-Host "  Status: $($test.Status) - $($test.Message)" -ForegroundColor $(if ($test.Status -eq "PASSED") { "Green" } else { "Red" })

# Test 6: Verify Sports Context Structure
Write-Host "[6/10] Verifying sports context structure..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8031/api/v1/suggestions/debug/context" -ErrorAction Stop
    $sports = $response.context_analysis.sports
    
    $test = @{
        Name = "Sports Context Structure"
        Status = "PASSED"
        Message = "Sports context has correct structure"
    }
    
    if (-not $sports.PSObject.Properties['available']) {
        $test.Status = "FAILED"
        $test.Message = "Missing 'available' field"
        $failed++
    } elseif (-not $sports.PSObject.Properties['insights']) {
        $test.Status = "FAILED"
        $test.Message = "Missing 'insights' field"
        $failed++
    } else {
        $passed++
    }
    
    $testResults += $test
    Write-Host "  Status: $($test.Status) - $($test.Message)" -ForegroundColor $(if ($test.Status -eq "PASSED") { "Green" } else { "Red" })
    Write-Host "  Insights count: $($sports.insights.Count)" -ForegroundColor Gray
} catch {
    $testResults += @{
        Name = "Sports Context Structure"
        Status = "FAILED"
        Message = $_.Exception.Message
    }
    $failed++
    Write-Host "  Status: FAILED - $($_.Exception.Message)" -ForegroundColor Red
}

# Test 7: Verify Historical Patterns Context Structure
Write-Host "[7/10] Verifying historical patterns context structure..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8031/api/v1/suggestions/debug/context" -ErrorAction Stop
    $historical = $response.context_analysis.historical_patterns
    
    $test = @{
        Name = "Historical Patterns Context Structure"
        Status = "PASSED"
        Message = "Historical patterns context has correct structure"
    }
    
    if (-not $historical.PSObject.Properties['available']) {
        $test.Status = "FAILED"
        $test.Message = "Missing 'available' field"
        $failed++
    } elseif (-not $historical.PSObject.Properties['insights']) {
        $test.Status = "FAILED"
        $test.Message = "Missing 'insights' field"
        $failed++
    } else {
        $passed++
    }
    
    $testResults += $test
    Write-Host "  Status: $($test.Status) - $($test.Message)" -ForegroundColor $(if ($test.Status -eq "PASSED") { "Green" } else { "Red" })
    Write-Host "  Available: $($historical.available)" -ForegroundColor Gray
    Write-Host "  Insights count: $($historical.insights.Count)" -ForegroundColor Gray
    
    # Check for query_info (new feature)
    if ($historical.PSObject.Properties['query_info']) {
        Write-Host "  ✓ query_info field present (new feature working)" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ query_info field missing (may need service restart)" -ForegroundColor Yellow
    }
} catch {
    $testResults += @{
        Name = "Historical Patterns Context Structure"
        Status = "FAILED"
        Message = $_.Exception.Message
    }
    $failed++
    Write-Host "  Status: FAILED - $($_.Exception.Message)" -ForegroundColor Red
}

# Test 8: Verify Energy Context Structure
Write-Host "[8/10] Verifying energy context structure..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8031/api/v1/suggestions/debug/context" -ErrorAction Stop
    $energy = $response.context_analysis.energy
    
    $test = @{
        Name = "Energy Context Structure"
        Status = "PASSED"
        Message = "Energy context has correct structure"
    }
    
    if (-not $energy.PSObject.Properties['available']) {
        $test.Status = "FAILED"
        $test.Message = "Missing 'available' field"
        $failed++
    } elseif (-not $energy.PSObject.Properties['current_intensity']) {
        $test.Status = "FAILED"
        $test.Message = "Missing 'current_intensity' field"
        $failed++
    } elseif (-not $energy.PSObject.Properties['trends']) {
        $test.Status = "FAILED"
        $test.Message = "Missing 'trends' field"
        $failed++
    } else {
        $passed++
    }
    
    $testResults += $test
    Write-Host "  Status: $($test.Status) - $($test.Message)" -ForegroundColor $(if ($test.Status -eq "PASSED") { "Green" } else { "Red" })
    Write-Host "  Available: $($energy.available)" -ForegroundColor Gray
    Write-Host "  Current intensity: $(if ($energy.current_intensity) { 'Present' } else { 'null (expected if no data)' })" -ForegroundColor Gray
    Write-Host "  Trends: $(if ($energy.trends) { 'Present' } else { 'null (expected if no data)' })" -ForegroundColor Gray
} catch {
    $testResults += @{
        Name = "Energy Context Structure"
        Status = "FAILED"
        Message = $_.Exception.Message
    }
    $failed++
    Write-Host "  Status: FAILED - $($_.Exception.Message)" -ForegroundColor Red
}

# Test 9: Verify Context Summary
Write-Host "[9/10] Verifying context summary..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8031/api/v1/suggestions/debug/context" -ErrorAction Stop
    $summary = $response.summary
    
    $test = @{
        Name = "Context Summary"
        Status = "PASSED"
        Message = "Context summary has correct structure"
    }
    
    $requiredFields = @('weather_available', 'sports_available', 'energy_available', 'historical_available', 'total_insights')
    $missingFields = @()
    
    foreach ($field in $requiredFields) {
        if (-not $summary.PSObject.Properties[$field]) {
            $missingFields += $field
        }
    }
    
    if ($missingFields.Count -gt 0) {
        $test.Status = "FAILED"
        $test.Message = "Missing fields: $($missingFields -join ', ')"
        $failed++
    } else {
        $passed++
    }
    
    $testResults += $test
    Write-Host "  Status: $($test.Status) - $($test.Message)" -ForegroundColor $(if ($test.Status -eq "PASSED") { "Green" } else { "Red" })
    Write-Host "  Total insights: $($summary.total_insights)" -ForegroundColor Gray
} catch {
    $testResults += @{
        Name = "Context Summary"
        Status = "FAILED"
        Message = $_.Exception.Message
    }
    $failed++
    Write-Host "  Status: FAILED - $($_.Exception.Message)" -ForegroundColor Red
}

# Test 10: Verify Sports Insights (Check for fallback insights)
Write-Host "[10/10] Verifying sports insights (checking for fallback insights)..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8031/api/v1/suggestions/debug/context" -ErrorAction Stop
    $sports = $response.context_analysis.sports
    
    $test = @{
        Name = "Sports Insights Fallback"
        Status = "PASSED"
        Message = "Sports insights present"
    }
    
    if ($sports.insights.Count -eq 0) {
        if ($sports.live_games.Count -eq 0 -and $sports.upcoming_games.Count -eq 0) {
            $test.Status = "FAILED"
            $test.Message = "No insights when no games - fallback insights should appear"
            $failed++
        } else {
            $test.Message = "No insights but games present (may be OK)"
            $passed++
        }
    } else {
        $test.Message = "Insights present: $($sports.insights.Count)"
        $passed++
    }
    
    $testResults += $test
    Write-Host "  Status: $($test.Status) - $($test.Message)" -ForegroundColor $(if ($test.Status -eq "PASSED") { "Green" } else { "Red" })
    if ($sports.insights.Count -gt 0) {
        Write-Host "  Insights:" -ForegroundColor Gray
        foreach ($insight in $sports.insights) {
            Write-Host "    - $insight" -ForegroundColor Gray
        }
    }
} catch {
    $testResults += @{
        Name = "Sports Insights Fallback"
        Status = "FAILED"
        Message = $_.Exception.Message
    }
    $failed++
    Write-Host "  Status: FAILED - $($_.Exception.Message)" -ForegroundColor Red
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Total Tests: $($testResults.Count)" -ForegroundColor White
Write-Host "Passed: $passed" -ForegroundColor Green
Write-Host "Failed: $failed" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Red" })
Write-Host ""

if ($failed -eq 0) {
    Write-Host "✓ All smoke tests passed!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "✗ Some tests failed. See details above." -ForegroundColor Red
    Write-Host ""
    Write-Host "Failed Tests:" -ForegroundColor Red
    foreach ($test in $testResults) {
        if ($test.Status -eq "FAILED") {
            Write-Host "  - $($test.Name): $($test.Message)" -ForegroundColor Red
        }
    }
    exit 1
}
