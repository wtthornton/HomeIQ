#!/usr/bin/env pwsh
# Test Automation API Script
# Tests an automation by calling the API endpoint directly without UI

param(
    [Parameter(Mandatory=$true)]
    [string]$Query,
    
    [string]$UserId = "api_test_user",
    [string]$BaseUrl = "http://localhost:8024/api/v1/ask-ai"
)

Write-Host "🧪 Testing Automation via API" -ForegroundColor Cyan
Write-Host "===============================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Query: $Query" -ForegroundColor Yellow
Write-Host "Base URL: $BaseUrl" -ForegroundColor Yellow
Write-Host ""

try {
    # Step 1: Create query
    Write-Host "📝 Step 1: Creating query..." -ForegroundColor Green
    
    $queryBody = @{
        query = $Query
        user_id = $UserId
    } | ConvertTo-Json
    
    $queryResponse = Invoke-RestMethod -Uri "$BaseUrl/query" `
        -Method POST `
        -ContentType "application/json" `
        -Body $queryBody
    
    $queryId = $queryResponse.query_id
    Write-Host "✅ Query created with ID: $queryId" -ForegroundColor Green
    Write-Host ""
    
    # Step 2: Get suggestions
    Write-Host "📋 Step 2: Getting suggestions..." -ForegroundColor Green
    $suggestions = $queryResponse.suggestions
    
    if ($suggestions.Count -eq 0) {
        Write-Host "❌ No suggestions generated" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ Found $($suggestions.Count) suggestions" -ForegroundColor Green
    Write-Host ""
    
    # Display suggestions
    for ($i = 0; $i -lt $suggestions.Count; $i++) {
        $suggestion = $suggestions[$i]
        Write-Host "Suggestion $($i + 1):" -ForegroundColor Cyan
        Write-Host "  Description: $($suggestion.description)" -ForegroundColor White
        Write-Host "  Confidence: $($suggestion.confidence)%" -ForegroundColor White
        Write-Host "  ID: $($suggestion.suggestion_id)" -ForegroundColor White
        Write-Host ""
    }
    
    # Step 3: Test first suggestion
    Write-Host "🧪 Step 3: Testing first suggestion..." -ForegroundColor Green
    
    $firstSuggestion = $suggestions[0]
    $suggestionId = $firstSuggestion.suggestion_id
    
    Write-Host "Testing suggestion: $($firstSuggestion.description)" -ForegroundColor Yellow
    Write-Host ""
    
    # Call test endpoint
    $testUrl = "$BaseUrl/query/$queryId/suggestions/$suggestionId/test"
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
