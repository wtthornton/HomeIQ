# Smoke Test for AI Pattern Service
# Tests key endpoints and functionality after deployment

$ErrorActionPreference = "Continue"
$results = @()
$baseUrl = "http://localhost:8034"

Write-Host "`n=== AI Pattern Service Smoke Test ===" -ForegroundColor Cyan
Write-Host "Service URL: $baseUrl`n" -ForegroundColor Gray

# Test 1: Root Endpoint
Write-Host "1. Testing root endpoint..." -ForegroundColor Yellow
try {
    $root = Invoke-RestMethod -Uri "$baseUrl/" -Method Get -ErrorAction Stop
    $results += [PSCustomObject]@{Test="Root Endpoint"; Status="PASS"; Details="$($root.service) v$($root.version)"}
    Write-Host "   ✓ Root endpoint: $($root.service) v$($root.version)" -ForegroundColor Green
} catch {
    $results += [PSCustomObject]@{Test="Root Endpoint"; Status="FAIL"; Details=$_.Exception.Message}
    Write-Host "   ✗ Root endpoint failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: Health Check
Write-Host "`n2. Testing health endpoint..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get -ErrorAction Stop
    $results += [PSCustomObject]@{Test="Health Check"; Status="PASS"; Details="$($health.status) - $($health.database)"}
    Write-Host "   ✓ Health: $($health.status) - Database: $($health.database)" -ForegroundColor Green
} catch {
    $results += [PSCustomObject]@{Test="Health Check"; Status="FAIL"; Details=$_.Exception.Message}
    Write-Host "   ✗ Health check failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Readiness Check
Write-Host "`n3. Testing readiness endpoint..." -ForegroundColor Yellow
try {
    $ready = Invoke-RestMethod -Uri "$baseUrl/ready" -Method Get -ErrorAction Stop
    $results += [PSCustomObject]@{Test="Readiness Check"; Status="PASS"; Details=$ready.status}
    Write-Host "   ✓ Readiness: $($ready.status)" -ForegroundColor Green
} catch {
    $results += [PSCustomObject]@{Test="Readiness Check"; Status="FAIL"; Details=$_.Exception.Message}
    Write-Host "   ✗ Readiness check failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: Liveness Check
Write-Host "`n4. Testing liveness endpoint..." -ForegroundColor Yellow
try {
    $live = Invoke-RestMethod -Uri "$baseUrl/live" -Method Get -ErrorAction Stop
    $results += [PSCustomObject]@{Test="Liveness Check"; Status="PASS"; Details=$live.status}
    Write-Host "   ✓ Liveness: $($live.status)" -ForegroundColor Green
} catch {
    $results += [PSCustomObject]@{Test="Liveness Check"; Status="FAIL"; Details=$_.Exception.Message}
    Write-Host "   ✗ Liveness check failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 5: Database Integrity
Write-Host "`n5. Testing database integrity check..." -ForegroundColor Yellow
try {
    $integrity = Invoke-RestMethod -Uri "$baseUrl/database/integrity" -Method Get -ErrorAction Stop
    $results += [PSCustomObject]@{Test="Database Integrity"; Status="PASS"; Details="$($integrity.status) - $($integrity.database)"}
    Write-Host "   ✓ Database Integrity: $($integrity.status) - $($integrity.database)" -ForegroundColor Green
} catch {
    $results += [PSCustomObject]@{Test="Database Integrity"; Status="FAIL"; Details=$_.Exception.Message}
    Write-Host "   ✗ Database integrity check failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 6: API Documentation
Write-Host "`n6. Testing API documentation endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/docs" -Method Get -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        $results += [PSCustomObject]@{Test="API Documentation"; Status="PASS"; Details="OpenAPI docs available"}
        Write-Host "   ✓ API Documentation: Available (HTTP $($response.StatusCode))" -ForegroundColor Green
    } else {
        $results += [PSCustomObject]@{Test="API Documentation"; Status="WARN"; Details="Status: $($response.StatusCode)"}
        Write-Host "   ⚠ API Documentation: Status $($response.StatusCode)" -ForegroundColor Yellow
    }
}
catch {
    $results += [PSCustomObject]@{Test="API Documentation"; Status="WARN"; Details=$_.Exception.Message}
    Write-Host "   ⚠ API Documentation: Could not verify" -ForegroundColor Yellow
}

# Test 7: Synergies Statistics
Write-Host "`n7. Testing synergies statistics endpoint..." -ForegroundColor Yellow
try {
    $stats = Invoke-RestMethod -Uri "$baseUrl/api/v1/synergies/statistics" -Method Get -ErrorAction Stop
    $results += [PSCustomObject]@{Test="Synergies Statistics"; Status="PASS"; Details="Total: $($stats.data.total_synergies)"}
    Write-Host "   ✓ Synergies Statistics: $($stats.data.total_synergies) total synergies" -ForegroundColor Green
} catch {
    $results += [PSCustomObject]@{Test="Synergies Statistics"; Status="FAIL"; Details=$_.Exception.Message}
    Write-Host "   ✗ Synergies statistics failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 8: Patterns List
Write-Host "`n8. Testing patterns list endpoint..." -ForegroundColor Yellow
try {
    $patterns = Invoke-RestMethod -Uri "$baseUrl/api/v1/patterns/list?limit=10" -Method Get -ErrorAction Stop
    $results += [PSCustomObject]@{Test="Patterns List"; Status="PASS"; Details="Endpoint responding"}
    Write-Host "   ✓ Patterns List: Endpoint responding" -ForegroundColor Green
} catch {
    $results += [PSCustomObject]@{Test="Patterns List"; Status="FAIL"; Details=$_.Exception.Message}
    Write-Host "   ✗ Patterns list failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 9: Docker Container Health
Write-Host "`n9. Testing Docker container health..." -ForegroundColor Yellow
try {
    $container = docker ps --filter "name=ai-pattern-service" --format "{{.Status}}" 2>&1
    if ($LASTEXITCODE -eq 0 -and $container -match "healthy|Up") {
        $results += [PSCustomObject]@{Test="Docker Container"; Status="PASS"; Details=$container.Trim()}
        Write-Host "   ✓ Docker Container: $($container.Trim())" -ForegroundColor Green
    } else {
        $results += [PSCustomObject]@{Test="Docker Container"; Status="WARN"; Details=$container.Trim()}
        Write-Host "   ⚠ Docker Container: $($container.Trim())" -ForegroundColor Yellow
    }
} catch {
    $results += [PSCustomObject]@{Test="Docker Container"; Status="FAIL"; Details=$_.Exception.Message}
    Write-Host "   ✗ Docker container check failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Summary
Write-Host "`n=== Smoke Test Summary ===" -ForegroundColor Cyan
$results | Format-Table -AutoSize

$passed = ($results | Where-Object { $_.Status -eq "PASS" }).Count
$failed = ($results | Where-Object { $_.Status -eq "FAIL" }).Count
$warned = ($results | Where-Object { $_.Status -eq "WARN" }).Count
$total = $results.Count

Write-Host "`nResults: $passed/$total passed, $failed failed, $warned warnings" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Red" })

if ($failed -eq 0) {
    Write-Host "`n✓ All critical tests passed! Service is operational." -ForegroundColor Green
    exit 0
} else {
    Write-Host "`n✗ Some tests failed. Please review the errors above." -ForegroundColor Red
    exit 1
}
