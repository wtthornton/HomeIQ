# Deployment Verification Script for Windows
# This script verifies that all components are working correctly after deployment

param(
    [switch]$Verbose
)

Write-Host "🚀 Starting deployment verification..." -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green

# Function to test API endpoint
function Test-Endpoint {
    param(
        [string]$Url,
        [string]$ExpectedField,
        [string]$ExpectedValue
    )
    
    try {
        Write-Host "Testing: $Url" -ForegroundColor Yellow
        
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -ErrorAction Stop
        $jsonResponse = $response.Content | ConvertFrom-Json
        
        if ($ExpectedField -and $ExpectedValue) {
            $actualValue = $jsonResponse.$ExpectedField
            if ($actualValue -eq $ExpectedValue) {
                Write-Host "✅ Endpoint $Url returns correct $ExpectedField`: $actualValue" -ForegroundColor Green
                return $true
            } else {
                Write-Host "❌ Endpoint $Url returned $ExpectedField`: $actualValue (expected: $ExpectedValue)" -ForegroundColor Red
                return $false
            }
        } else {
            Write-Host "✅ Endpoint $Url is accessible" -ForegroundColor Green
            return $true
        }
    }
    catch {
        Write-Host "❌ Endpoint $Url is not accessible: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Function to test dashboard
function Test-Dashboard {
    Write-Host "Testing dashboard functionality..." -ForegroundColor Yellow
    
    # Test dashboard loads
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -ErrorAction Stop
        Write-Host "✅ Dashboard loads successfully" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Dashboard is not accessible: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
    
    # Test dashboard API calls (simulate what frontend does)
    Write-Host "Testing dashboard API integration..." -ForegroundColor Yellow
    
    # Test enhanced health endpoint (admin-api external port 8004)
    try {
        $healthResponse = Invoke-WebRequest -Uri "http://localhost:8004/api/v1/health" -UseBasicParsing
        $healthJson = $healthResponse.Content | ConvertFrom-Json
        
        if ($healthJson.dependencies) {
            Write-Host "✅ Enhanced health endpoint returns dependency information" -ForegroundColor Green
        } else {
            Write-Host "❌ Enhanced health endpoint missing dependency information" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "❌ Enhanced health endpoint test failed: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
    
    # Test stats endpoint (admin-api external port 8004; may require auth)
    try {
        $statsResponse = Invoke-WebRequest -Uri "http://localhost:8004/api/v1/stats" -UseBasicParsing -ErrorAction SilentlyContinue
        if (-not $statsResponse) { $statsResponse = $null }
        $statsJson = $statsResponse.Content | ConvertFrom-Json
        
        if ($statsJson.metrics -or $statsJson.timestamp) {
            Write-Host "✅ Stats endpoint returns data" -ForegroundColor Green
        } elseif ($statsResponse.StatusCode -eq 401) {
            Write-Host "✅ Stats endpoint reachable (requires API key)" -ForegroundColor Green
        } else {
            Write-Host "❌ Stats endpoint missing expected data" -ForegroundColor Red
            return $false
        }
    }
    catch {
        if ($_.Exception.Response.StatusCode.value__ -eq 401) {
            Write-Host "✅ Stats endpoint reachable (401 - requires API key)" -ForegroundColor Green
        } else {
            Write-Host "❌ Stats endpoint test failed: $($_.Exception.Message)" -ForegroundColor Red
            return $false
        }
    }
    
    return $true
}

# Function to check service logs
function Test-ServiceLogs {
    Write-Host "Checking service logs for errors..." -ForegroundColor Yellow
    
    # Check admin-api logs
    try {
        $adminLogs = docker logs homeiq-admin 2>&1 | Select-String -Pattern "error|exception|failed" -CaseSensitive:$false | Select-Object -Last 5
        if ($adminLogs) {
            Write-Host "⚠️  Admin API has recent errors:" -ForegroundColor Yellow
            $adminLogs | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
        } else {
            Write-Host "✅ Admin API logs are clean" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "⚠️  Could not check admin-api logs: $($_.Exception.Message)" -ForegroundColor Yellow
    }
    
    # Check dashboard logs
    try {
        $dashboardLogs = docker logs homeiq-dashboard 2>&1 | Select-String -Pattern "error|exception|failed" -CaseSensitive:$false | Select-Object -Last 5
        if ($dashboardLogs) {
            Write-Host "⚠️  Dashboard has recent errors:" -ForegroundColor Yellow
            $dashboardLogs | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
        } else {
            Write-Host "✅ Dashboard logs are clean" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "⚠️  Could not check dashboard logs: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# Function to verify TypeScript types
function Test-TypeScriptTypes {
    Write-Host "Verifying TypeScript types..." -ForegroundColor Yellow
    
    $healthTypesFile = "domains/core-platform/health-dashboard/src/types/health.ts"
    
    if (Test-Path $healthTypesFile) {
        $content = Get-Content $healthTypesFile -Raw
        
        if ($content -match "ServiceHealthResponse") {
            Write-Host "✅ ServiceHealthResponse type is defined" -ForegroundColor Green
        } else {
            Write-Host "❌ ServiceHealthResponse type is missing" -ForegroundColor Red
            return $false
        }
        
        if ($content -match "DependencyHealth") {
            Write-Host "✅ DependencyHealth type is defined" -ForegroundColor Green
        } else {
            Write-Host "❌ DependencyHealth type is missing" -ForegroundColor Red
            return $false
        }
    } else {
        Write-Host "❌ Health types file not found: $healthTypesFile" -ForegroundColor Red
        return $false
    }
    
    return $true
}

# Main verification process
Write-Host "1. Verifying service health..." -ForegroundColor Cyan
if (-not (Test-Endpoint "http://localhost:8004/health" "status" "healthy")) { exit 1 }
if (-not (Test-Endpoint "http://localhost:8004/api/health" "status" "healthy")) { exit 1 }

Write-Host ""
Write-Host "2. Verifying enhanced health endpoint..." -ForegroundColor Cyan
if (-not (Test-Endpoint "http://localhost:8004/api/v1/health" "status" "healthy")) { exit 1 }

Write-Host ""
Write-Host "3. Verifying stats endpoint..." -ForegroundColor Cyan
# Stats may return 401 without API key - endpoint existence is enough
try { $null = Invoke-WebRequest -Uri "http://localhost:8004/api/v1/stats" -UseBasicParsing -ErrorAction Stop; Write-Host "✅ Stats endpoint returns data" -ForegroundColor Green } catch { if ($_.Exception.Response.StatusCode.value__ -eq 401) { Write-Host "✅ Stats endpoint reachable (requires API key)" -ForegroundColor Green } else { Write-Host "❌ Stats endpoint failed: $($_.Exception.Message)" -ForegroundColor Red; exit 1 } }

Write-Host ""
Write-Host "4. Verifying alerts endpoint..." -ForegroundColor Cyan
try {
    $alertsResponse = Invoke-WebRequest -Uri "http://localhost:8004/api/v1/stats/alerts" -UseBasicParsing -ErrorAction Stop
    if ($alertsResponse.StatusCode -eq 200) {
        Write-Host "✅ Alerts endpoint returns data" -ForegroundColor Green
    } else {
        Write-Host "✅ Alerts endpoint reachable (HTTP $($alertsResponse.StatusCode))" -ForegroundColor Green
    }
} catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 401) {
        Write-Host "✅ Alerts endpoint reachable (401 - requires API key)" -ForegroundColor Green
    } else {
        Write-Host "❌ Alerts endpoint failed: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "5. Verifying dashboard..." -ForegroundColor Cyan
if (-not (Test-Dashboard)) { exit 1 }

Write-Host ""
Write-Host "6. Checking service logs..." -ForegroundColor Cyan
Test-ServiceLogs

Write-Host ""
Write-Host "7. Verifying TypeScript types..." -ForegroundColor Cyan
if (-not (Test-TypeScriptTypes)) { exit 1 }

Write-Host ""
Write-Host "==================================" -ForegroundColor Green
Write-Host "🎉 Deployment verification completed successfully!" -ForegroundColor Green
Write-Host "All systems are operational and the dashboard should be working correctly." -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "- Open http://localhost:3000 in your browser" -ForegroundColor White
Write-Host "- Verify the dashboard shows 'ALL SYSTEMS OPERATIONAL'" -ForegroundColor White
Write-Host "- Check that all core system components show healthy status" -ForegroundColor White
Write-Host "- Test navigation between dashboard tabs" -ForegroundColor White
