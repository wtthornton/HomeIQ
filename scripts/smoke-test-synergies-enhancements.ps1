# Smoke Test for Synergies Enhancements
# Tests all new synergy detection engines and features

$ErrorActionPreference = "Continue"
$results = @()
$baseUrl = "http://localhost:8034"

Write-Host "`n=== Synergies Enhancements Smoke Test ===" -ForegroundColor Cyan
Write-Host "Service URL: $baseUrl`n" -ForegroundColor Gray

# Test 1: Health Check
Write-Host "1. Testing health endpoint..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get -ErrorAction Stop
    if ($health.status -eq "ok" -and $health.database -eq "connected") {
        $results += [PSCustomObject]@{Test="Health Check"; Status="PASS"; Details="$($health.status) - $($health.database)"}
        Write-Host "   ✓ Health: $($health.status) - Database: $($health.database)" -ForegroundColor Green
    } else {
        $results += [PSCustomObject]@{Test="Health Check"; Status="WARN"; Details="Status: $($health.status)"}
        Write-Host "   ⚠ Health: $($health.status)" -ForegroundColor Yellow
    }
} catch {
    $results += [PSCustomObject]@{Test="Health Check"; Status="FAIL"; Details=$_.Exception.Message}
    Write-Host "   ✗ Health check failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: Service Info
Write-Host "`n2. Testing service info..." -ForegroundColor Yellow
try {
    $info = Invoke-RestMethod -Uri "$baseUrl/" -Method Get -ErrorAction Stop
    $results += [PSCustomObject]@{Test="Service Info"; Status="PASS"; Details="$($info.service) v$($info.version)"}
    Write-Host "   ✓ Service: $($info.service) v$($info.version)" -ForegroundColor Green
} catch {
    $results += [PSCustomObject]@{Test="Service Info"; Status="FAIL"; Details=$_.Exception.Message}
    Write-Host "   ✗ Service info failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Synergy API
Write-Host "`n3. Testing synergy API..." -ForegroundColor Yellow
try {
    $synergies = Invoke-RestMethod -Uri "$baseUrl/api/v1/synergies/list?limit=5" -Method Get -ErrorAction Stop
    if ($synergies.success) {
        $results += [PSCustomObject]@{Test="Synergy API"; Status="PASS"; Details="Total: $($synergies.data.total)"}
        Write-Host "   ✓ Synergy API: $($synergies.data.total) synergies found" -ForegroundColor Green
    } else {
        $results += [PSCustomObject]@{Test="Synergy API"; Status="WARN"; Details="API responded but success=false"}
        Write-Host "   ⚠ Synergy API: Response indicates failure" -ForegroundColor Yellow
    }
} catch {
    $results += [PSCustomObject]@{Test="Synergy API"; Status="FAIL"; Details=$_.Exception.Message}
    Write-Host "   ✗ Synergy API failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: Check for New Context Types
Write-Host "`n4. Testing new context types..." -ForegroundColor Yellow
try {
    $synergies = Invoke-RestMethod -Uri "$baseUrl/api/v1/synergies/list?limit=50" -Method Get -ErrorAction Stop
    if ($synergies.success -and $synergies.data.synergies) {
        $contextTypes = $synergies.data.synergies | Where-Object { $_.synergy_type -match "context" } | Select-Object -ExpandProperty synergy_type -Unique
        $newTypes = $contextTypes | Where-Object { $_ -match "sports|carbon|calendar" }
        
        if ($newTypes) {
            $results += [PSCustomObject]@{Test="New Context Types"; Status="PASS"; Details="Found: $($newTypes -join ', ')"}
            Write-Host "   ✓ New context types found: $($newTypes -join ', ')" -ForegroundColor Green
        } else {
            $results += [PSCustomObject]@{Test="New Context Types"; Status="INFO"; Details="No new context types yet (may need pattern analysis)"}
            Write-Host "   ℹ New context types: Not yet detected (run pattern analysis)" -ForegroundColor Cyan
        }
    } else {
        $results += [PSCustomObject]@{Test="New Context Types"; Status="INFO"; Details="No synergies available yet"}
        Write-Host "   ℹ New context types: No synergies available" -ForegroundColor Cyan
    }
} catch {
    $results += [PSCustomObject]@{Test="New Context Types"; Status="WARN"; Details=$_.Exception.Message}
    Write-Host "   ⚠ Could not check context types: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Test 5: Check for Energy Savings Data
Write-Host "`n5. Testing energy savings calculation..." -ForegroundColor Yellow
try {
    $synergies = Invoke-RestMethod -Uri "$baseUrl/api/v1/synergies/list?limit=50" -Method Get -ErrorAction Stop
    if ($synergies.success -and $synergies.data.synergies) {
        $energySynergies = $synergies.data.synergies | Where-Object { $_.context_metadata.energy -or $_.energy_savings_score }
        
        if ($energySynergies) {
            $count = $energySynergies.Count
            $results += [PSCustomObject]@{Test="Energy Savings"; Status="PASS"; Details="$count synergies with energy data"}
            Write-Host "   ✓ Energy savings: $count synergies have energy data" -ForegroundColor Green
        } else {
            $results += [PSCustomObject]@{Test="Energy Savings"; Status="INFO"; Details="No energy data yet (may need pattern analysis)"}
            Write-Host "   ℹ Energy savings: Not yet calculated (run pattern analysis)" -ForegroundColor Cyan
        }
    } else {
        $results += [PSCustomObject]@{Test="Energy Savings"; Status="INFO"; Details="No synergies available yet"}
        Write-Host "   ℹ Energy savings: No synergies available" -ForegroundColor Cyan
    }
} catch {
    $results += [PSCustomObject]@{Test="Energy Savings"; Status="WARN"; Details=$_.Exception.Message}
    Write-Host "   ⚠ Could not check energy savings: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Test 6: Container Logs - Check Engine Initialization
Write-Host "`n6. Testing engine initialization in logs..." -ForegroundColor Yellow
try {
    $logs = docker compose logs ai-pattern-service --tail 100 2>&1
    $engines = @("EnergySavingsCalculator", "SpatialIntelligence", "TemporalSynergy", "RelationshipDiscovery", "CapabilityAnalyzer")
    $found = @()
    
    foreach ($engine in $engines) {
        if ($logs -match $engine) {
            $found += $engine
        }
    }
    
    if ($found.Count -gt 0) {
        $results += [PSCustomObject]@{Test="Engine Initialization"; Status="PASS"; Details="Found: $($found -join ', ')"}
        Write-Host "   ✓ Engines initialized: $($found -join ', ')" -ForegroundColor Green
    } else {
        $results += [PSCustomObject]@{Test="Engine Initialization"; Status="WARN"; Details="No engine logs found (may be disabled)"}
        Write-Host "   ⚠ Engine initialization: No logs found" -ForegroundColor Yellow
    }
} catch {
    $results += [PSCustomObject]@{Test="Engine Initialization"; Status="WARN"; Details=$_.Exception.Message}
    Write-Host "   ⚠ Could not check logs: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Test 7: Container Health
Write-Host "`n7. Testing container health..." -ForegroundColor Yellow
try {
    $container = docker ps --filter "name=ai-pattern-service" --format "{{.Status}}" 2>&1
    if ($LASTEXITCODE -eq 0 -and $container) {
        if ($container -match "healthy|Up") {
            $results += [PSCustomObject]@{Test="Container Health"; Status="PASS"; Details=$container.Trim()}
            Write-Host "   ✓ Container: $($container.Trim())" -ForegroundColor Green
        } else {
            $results += [PSCustomObject]@{Test="Container Health"; Status="WARN"; Details=$container.Trim()}
            Write-Host "   ⚠ Container: $($container.Trim())" -ForegroundColor Yellow
        }
    } else {
        $results += [PSCustomObject]@{Test="Container Health"; Status="FAIL"; Details="Container not found"}
        Write-Host "   ✗ Container: Not found" -ForegroundColor Red
    }
} catch {
    $results += [PSCustomObject]@{Test="Container Health"; Status="FAIL"; Details=$_.Exception.Message}
    Write-Host "   ✗ Container check failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Summary
Write-Host "`n=== Smoke Test Summary ===" -ForegroundColor Cyan
$results | Format-Table -AutoSize

$passed = ($results | Where-Object { $_.Status -eq "PASS" }).Count
$failed = ($results | Where-Object { $_.Status -eq "FAIL" }).Count
$warned = ($results | Where-Object { $_.Status -eq "WARN" }).Count
$info = ($results | Where-Object { $_.Status -eq "INFO" }).Count
$total = $results.Count

Write-Host "`nResults: $passed/$total passed, $failed failed, $warned warnings, $info info" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Red" })

if ($failed -eq 0) {
    Write-Host "`n✓ All critical tests passed! Service is operational." -ForegroundColor Green
    exit 0
} else {
    Write-Host "`n✗ Some tests failed. Please review the errors above." -ForegroundColor Red
    exit 1
}
