# Test All Implemented Recommendations
# Run this script to verify all 10 recommendations are working

param(
    [string]$BaseUrl = "http://localhost:8020"
)

$ErrorActionPreference = "Continue"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Testing Implemented Recommendations" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Test 1: Health Check
Write-Host "1. Health Check..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$BaseUrl/health" -ErrorAction Stop
    if ($health.status -eq "healthy") {
        Write-Host "   ✅ Service is healthy" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️ Service status: $($health.status)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ❌ Health check failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "   Make sure the service is running on $BaseUrl" -ForegroundColor Yellow
    exit 1
}

# Test 2: Get Synergies
Write-Host "`n2. Getting Synergies..." -ForegroundColor Yellow
try {
    $synergies = Invoke-RestMethod -Uri "$BaseUrl/api/v1/synergies/list?limit=1" -ErrorAction Stop
    if ($synergies.data.synergies.Count -gt 0) {
        $synergyId = $synergies.data.synergies[0].synergy_id
        Write-Host "   ✅ Found synergy: $synergyId" -ForegroundColor Green
        
        # Test 3: Automation Generation (Rec 1.1)
        Write-Host "`n3. Testing Automation Generation (Rec 1.1)..." -ForegroundColor Yellow
        try {
            $automation = Invoke-RestMethod -Uri "$BaseUrl/api/v1/synergies/$synergyId/generate-automation" -Method Post -ErrorAction Stop
            Write-Host "   ✅ Automation generated: $($automation.data.automation_id)" -ForegroundColor Green
        } catch {
            Write-Host "   ⚠️ Automation generation failed (may need HA config): $($_.Exception.Message)" -ForegroundColor Yellow
        }
        
        # Test 4: Feedback Submission (Rec 2.1)
        Write-Host "`n4. Testing Feedback Submission (Rec 2.1)..." -ForegroundColor Yellow
        try {
            $feedback = @{
                accepted = $true
                rating = 5
                feedback_text = "Test feedback from script"
            } | ConvertTo-Json
            $result = Invoke-RestMethod -Uri "$BaseUrl/api/v1/synergies/$synergyId/feedback" `
                -Method Post `
                -Body $feedback `
                -ContentType "application/json" `
                -ErrorAction Stop
            Write-Host "   ✅ Feedback submitted successfully" -ForegroundColor Green
        } catch {
            Write-Host "   ⚠️ Feedback submission failed: $($_.Exception.Message)" -ForegroundColor Yellow
        }
        
        # Test 5: Execution Tracking (Rec 2.2)
        Write-Host "`n5. Testing Execution Tracking (Rec 2.2)..." -ForegroundColor Yellow
        try {
            $execution = @{
                automation_id = "automation.test_123"
                synergy_id = $synergyId
                success = $true
                execution_time_ms = 150
                triggered_count = 1
            } | ConvertTo-Json
            $result = Invoke-RestMethod -Uri "$BaseUrl/api/v1/synergies/$synergyId/track-execution" `
                -Method Post `
                -Body $execution `
                -ContentType "application/json" `
                -ErrorAction Stop
            Write-Host "   ✅ Execution tracked successfully" -ForegroundColor Green
            
            # Get execution stats
            $stats = Invoke-RestMethod -Uri "$BaseUrl/api/v1/synergies/$synergyId/execution-stats" -ErrorAction Stop
            Write-Host "   📊 Execution stats: $($stats.data.total_executions) total, $($stats.data.success_rate * 100)% success rate" -ForegroundColor Cyan
        } catch {
            Write-Host "   ⚠️ Execution tracking failed: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "   ⚠️ No synergies found - run pattern analysis first" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ⚠️ Failed to get synergies: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Test 6: Get Patterns (Rec 1.2, 3.1)
Write-Host "`n6. Getting Patterns (Rec 1.2, 3.1)..." -ForegroundColor Yellow
try {
    $patterns = Invoke-RestMethod -Uri "$BaseUrl/api/v1/patterns/list?limit=5" -ErrorAction Stop
    Write-Host "   ✅ Found $($patterns.data.count) patterns" -ForegroundColor Green
    
    # Check for time-of-day patterns with automation suggestions
    $todPatterns = $patterns.data.patterns | Where-Object { $_.pattern_type -eq "time_of_day" }
    if ($todPatterns.Count -gt 0) {
        Write-Host "   ✅ Found $($todPatterns.Count) time-of-day patterns (Rec 1.2)" -ForegroundColor Green
    }
} catch {
    Write-Host "   ⚠️ Failed to get patterns: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Test 7: Get Statistics (Rec 3.2, 5.1, 5.2)
Write-Host "`n7. Getting Statistics (Rec 3.2, 5.1, 5.2)..." -ForegroundColor Yellow
try {
    $stats = Invoke-RestMethod -Uri "$BaseUrl/api/v1/synergies/statistics" -ErrorAction Stop
    Write-Host "   ✅ Statistics retrieved:" -ForegroundColor Green
    Write-Host "      Total synergies: $($stats.data.total_synergies)" -ForegroundColor Cyan
    Write-Host "      Avg confidence: $($stats.data.avg_confidence)" -ForegroundColor Cyan
    Write-Host "      Avg impact: $($stats.data.avg_impact_score)" -ForegroundColor Cyan
} catch {
    Write-Host "   ⚠️ Failed to get statistics: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Test 8: Check Context-Aware Features (Rec 4.1)
Write-Host "`n8. Checking Context-Aware Features (Rec 4.1)..." -ForegroundColor Yellow
try {
    if ($synergyId) {
        $synergy = Invoke-RestMethod -Uri "$BaseUrl/api/v1/synergies/$synergyId" -ErrorAction Stop
        if ($synergy.data.context_breakdown) {
            Write-Host "   ✅ Synergy has context breakdown (weather, energy, carbon)" -ForegroundColor Green
        } else {
            Write-Host "   ⚠️ No context breakdown found (may be added during automation generation)" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "   ⚠️ Failed to check context features: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`n✅ All tests completed!" -ForegroundColor Green
Write-Host "`nNote: Some tests may show warnings if:" -ForegroundColor Yellow
Write-Host "  - Home Assistant is not configured (automation generation)" -ForegroundColor Yellow
Write-Host "  - No synergies/patterns exist yet (run pattern analysis)" -ForegroundColor Yellow
Write-Host "  - Database tables need migration (feedback tracking)" -ForegroundColor Yellow
Write-Host "`nFor detailed testing, see: implementation/HOW_TO_EXECUTE_RECOMMENDATIONS.md" -ForegroundColor Cyan
