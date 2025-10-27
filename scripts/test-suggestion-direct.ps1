#!/usr/bin/env pwsh
# Test Existing Suggestion Script
# Tests a suggestion that already exists by query_id and suggestion_id

param(
    [Parameter(Mandatory=$true)]
    [string]$QueryId,
    
    [Parameter(Mandatory=$true)]
    [string]$SuggestionId,
    
    [string]$BaseUrl = "http://localhost:8024/api/v1/ask-ai"
)

Write-Host "🧪 Testing Existing Suggestion" -ForegroundColor Cyan
Write-Host "===============================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Query ID: $QueryId" -ForegroundColor Yellow
Write-Host "Suggestion ID: $SuggestionId" -ForegroundColor Yellow
Write-Host ""

try {
    # Call test endpoint directly
    Write-Host "🧪 Testing suggestion..." -ForegroundColor Green
    
    $testUrl = "$BaseUrl/query/$QueryId/suggestions/$SuggestionId/test"
    Write-Host "Calling: $testUrl" -ForegroundColor Gray
    Write-Host ""
    
    $testResponse = Invoke-RestMethod -Uri $testUrl `
        -Method POST `
        -ContentType "application/json"
    
    # Display results
    Write-Host "✅ Test Results:" -ForegroundColor Green
    Write-Host "  Valid: $($testResponse.valid)" -ForegroundColor $(if ($testResponse.valid) { "Green" } else { "Red" })
    Write-Host "  Executed: $($testResponse.executed)" -ForegroundColor $(if ($testResponse.executed) { "Green" } else { "Yellow" })
    Write-Host "  Automation ID: $($testResponse.automation_id)" -ForegroundColor White
    Write-Host "  Message: $($testResponse.message)" -ForegroundColor White
    Write-Host ""
    
    # Display validation details
    if ($testResponse.validation_details) {
        $validation = $testResponse.validation_details
        
        if ($validation.warnings -and $validation.warnings.Count -gt 0) {
            Write-Host "⚠️  Warnings:" -ForegroundColor Yellow
            foreach ($warning in $validation.warnings) {
                Write-Host "   - $warning" -ForegroundColor Yellow
            }
            Write-Host ""
        }
        
        if ($validation.entity_count) {
            Write-Host "  Entity Count: $($validation.entity_count)" -ForegroundColor White
            Write-Host ""
        }
    }
    
    Write-Host "===============================" -ForegroundColor Cyan
    Write-Host "✅ Test Complete!" -ForegroundColor Green
    
    if ($testResponse.executed) {
        Write-Host ""
        Write-Host "💡 Check your Home Assistant devices to see the automation in action!" -ForegroundColor Cyan
        Write-Host "   The test automation has been created with [TEST] prefix and is now disabled." -ForegroundColor Cyan
    }
    
} catch {
    Write-Host ""
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
    
    if ($_.ErrorDetails.Message) {
        Write-Host "Details: $($_.ErrorDetails.Message)" -ForegroundColor Red
    }
    
    exit 1
}
