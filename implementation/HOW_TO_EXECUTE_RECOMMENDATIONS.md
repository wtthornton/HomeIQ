# How to Execute and Test the Implemented Recommendations

This guide shows you how to run and test all 10 implemented recommendations.

## Prerequisites

1. **Services Running**: Start the required services
2. **Database**: SQLite database should be initialized
3. **Home Assistant**: Configured (for automation generation)

## Step 1: Start Services

### Option A: Using Docker Compose (Recommended)

```powershell
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f ai-pattern-service
```

### Option B: Run Service Directly

```powershell
cd services/ai-pattern-service

# Install dependencies (if needed)
pip install -r requirements.txt

# Run the service
python -m uvicorn src.main:app --host 0.0.0.0 --port 8020 --reload
```

## Step 2: Verify Service Health

```powershell
# Health check
Invoke-RestMethod -Uri "http://localhost:8020/health"

# Expected response:
# {
#   "status": "healthy",
#   "service": "ai-pattern-service",
#   "version": "...",
#   "database": "connected"
# }
```

## Step 3: Test Each Recommendation

### Recommendation 1.1: Synergy-to-Automation Converter

**Test via UI:**
1. Open the AI Automation UI: `http://localhost:3001` (or your UI port)
2. Navigate to "Synergies" tab
3. Click "Create Automation" on any synergy
4. Verify automation is created in Home Assistant

**Test via API:**
```powershell
# Get a synergy ID first
$synergies = Invoke-RestMethod -Uri "http://localhost:8020/api/v1/synergies/list?limit=1"
$synergyId = $synergies.data.synergies[0].synergy_id

# Generate automation
Invoke-RestMethod -Uri "http://localhost:8020/api/v1/synergies/$synergyId/generate-automation" -Method Post

# Expected response:
# {
#   "success": true,
#   "data": {
#     "automation_id": "automation.synergy_xxx",
#     "automation_yaml": "...",
#     "deployment_status": "deployed"
#   }
# }
```

### Recommendation 1.2: Pattern-Based Automation Suggestions

**Test via API:**
```powershell
# Get time-of-day patterns
$patterns = Invoke-RestMethod -Uri "http://localhost:8020/api/v1/patterns/list?pattern_type=time_of_day&limit=5"

# Check if patterns have automation suggestions
$patterns.data.patterns | ForEach-Object {
    if ($_.automation_suggestion) {
        Write-Host "Pattern $($_.pattern_id) has automation suggestion: $($_.automation_suggestion.description)"
    }
}
```

### Recommendation 2.1: Feedback Integration

**Submit Feedback:**
```powershell
# Get a synergy ID
$synergies = Invoke-RestMethod -Uri "http://localhost:8020/api/v1/synergies/list?limit=1"
$synergyId = $synergies.data.synergies[0].synergy_id

# Submit positive feedback
$feedback = @{
    accepted = $true
    rating = 5
    feedback_text = "This automation works great!"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8020/api/v1/synergies/$synergyId/feedback" `
    -Method Post `
    -Body $feedback `
    -ContentType "application/json"

# Verify feedback affects pattern confidence
# (Patterns with positive feedback should have higher confidence in next analysis)
```

### Recommendation 2.2: Automation Execution Tracking

**Track Automation Execution:**
```powershell
# Track successful execution
$execution = @{
    automation_id = "automation.synergy_xxx"
    synergy_id = $synergyId
    success = $true
    execution_time_ms = 150
    triggered_count = 1
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8020/api/v1/synergies/$synergyId/track-execution" `
    -Method Post `
    -Body $execution `
    -ContentType "application/json"

# Get execution statistics
Invoke-RestMethod -Uri "http://localhost:8020/api/v1/synergies/$synergyId/execution-stats"

# Expected response:
# {
#   "success": true,
#   "data": {
#     "total_executions": 1,
#     "successful_executions": 1,
#     "failed_executions": 0,
#     "success_rate": 1.0
#   }
# }
```

### Recommendation 3.1: Pattern-to-Synergy Generation

**Trigger Pattern Analysis:**
```powershell
# The scheduler automatically runs pattern analysis
# Check job status (if scheduler endpoint exists)
# Or check synergies - pattern-based synergies will be included

$synergies = Invoke-RestMethod -Uri "http://localhost:8020/api/v1/synergies/list?limit=10"

# Pattern-based synergies will have metadata indicating they came from patterns
$synergies.data.synergies | Where-Object { $_.metadata.source -eq "pattern_based" }
```

### Recommendation 3.2: Pattern-Validated Synergy Ranking

**Verify Ranking:**
```powershell
# Get synergies ordered by priority (includes pattern validation boost)
$synergies = Invoke-RestMethod -Uri "http://localhost:8020/api/v1/synergies/list?order_by_priority=true&limit=10"

# Pattern-validated synergies should rank higher
$synergies.data.synergies | ForEach-Object {
    Write-Host "Synergy: $($_.synergy_id), Confidence: $($_.confidence), Pattern Validated: $($_.metadata.pattern_validated)"
}
```

### Recommendation 4.1: Context-Aware Automation Parameters

**Test Context-Aware Generation:**
```powershell
# Generate automation with context breakdown
$synergy = Invoke-RestMethod -Uri "http://localhost:8020/api/v1/synergies/$synergyId"

# Check if context_breakdown exists
if ($synergy.data.context_breakdown) {
    Write-Host "Context breakdown:"
    $synergy.data.context_breakdown | ConvertTo-Json -Depth 3
    
    # Generate automation - it will use context-aware parameters
    $result = Invoke-RestMethod -Uri "http://localhost:8020/api/v1/synergies/$synergyId/generate-automation" -Method Post
    
    # Check automation YAML for context-aware adjustments
    Write-Host "Automation YAML:"
    $result.data.automation_yaml
}
```

### Recommendation 4.2: Automation Testing Before Deployment

**Verify Pre-Deployment Validation:**
```powershell
# Generate automation - validation happens automatically
$result = Invoke-RestMethod -Uri "http://localhost:8020/api/v1/synergies/$synergyId/generate-automation" -Method Post

# Check deployment_status
if ($result.data.deployment_status -eq "deployed") {
    Write-Host "✅ Automation passed pre-deployment validation"
} elseif ($result.data.deployment_status -eq "validation_failed") {
    Write-Host "❌ Automation failed validation: $($result.data.validation_errors)"
}
```

### Recommendation 5.1: Pattern Evolution Tracking

**Check Pattern Evolution:**
```powershell
# Run pattern analysis multiple times to see evolution
# (Pattern evolution is tracked automatically during analysis)

# Get pattern statistics
$stats = Invoke-RestMethod -Uri "http://localhost:8020/api/v1/patterns/stats"

# Evolution tracking happens in the background
# Check logs for evolution analysis:
docker logs homeiq-ai-pattern-service | Select-String "Pattern evolution"
```

### Recommendation 5.2: Community Pattern Learning

**Test Community Enhancement:**
```powershell
# Community pattern enhancement happens automatically
# Patterns similar to community favorites get confidence boost

# Get patterns and check confidence
$patterns = Invoke-RestMethod -Uri "http://localhost:8020/api/v1/patterns/list?limit=10"

# Patterns with community_enhanced flag have been boosted
$patterns.data.patterns | Where-Object { $_.community_enhanced } | ForEach-Object {
    Write-Host "Pattern $($_.pattern_id) enhanced by community patterns (confidence: $($_.confidence))"
}
```

## Step 4: Run Comprehensive Tests

### Unit Tests
```powershell
cd services/ai-pattern-service
pytest -m unit -v
```

### Integration Tests
```powershell
pytest -m integration -v
```

### E2E Tests (Requires Running Service)
```powershell
# Make sure service is running on port 8020
pytest -m e2e -v
```

### All Tests
```powershell
pytest -v
```

## Step 5: Verify Quality Scores

```powershell
# Review all implemented files
python scripts/final_quality_review.py

# Or review individual files
python -m tapps_agents.cli reviewer score services/ai-pattern-service/src/services/feedback_client.py
python -m tapps_agents.cli reviewer score services/ai-pattern-service/src/services/pattern_evolution_tracker.py
python -m tapps_agents.cli reviewer score services/ai-pattern-service/src/services/community_pattern_enhancer.py
```

## Step 6: Monitor Service Logs

```powershell
# View real-time logs
docker logs -f homeiq-ai-pattern-service

# Look for:
# - "Pattern evolution analysis complete"
# - "Enhanced pattern confidence"
# - "Automation execution tracked"
# - "Feedback stored"
```

## Quick Test Script

Create a PowerShell script to test all features:

```powershell
# test-recommendations.ps1
$baseUrl = "http://localhost:8020"

Write-Host "Testing Recommendations..." -ForegroundColor Green

# 1. Health check
Write-Host "`n1. Health Check..." -ForegroundColor Yellow
$health = Invoke-RestMethod -Uri "$baseUrl/health"
Write-Host "Status: $($health.status)" -ForegroundColor $(if ($health.status -eq "healthy") { "Green" } else { "Red" })

# 2. Get synergies
Write-Host "`n2. Getting Synergies..." -ForegroundColor Yellow
$synergies = Invoke-RestMethod -Uri "$baseUrl/api/v1/synergies/list?limit=1"
if ($synergies.data.synergies.Count -gt 0) {
    $synergyId = $synergies.data.synergies[0].synergy_id
    Write-Host "Found synergy: $synergyId" -ForegroundColor Green
    
    # 3. Test automation generation
    Write-Host "`n3. Testing Automation Generation..." -ForegroundColor Yellow
    try {
        $automation = Invoke-RestMethod -Uri "$baseUrl/api/v1/synergies/$synergyId/generate-automation" -Method Post
        Write-Host "✅ Automation generated: $($automation.data.automation_id)" -ForegroundColor Green
    } catch {
        Write-Host "⚠️ Automation generation failed (may need HA config): $($_.Exception.Message)" -ForegroundColor Yellow
    }
    
    # 4. Test feedback
    Write-Host "`n4. Testing Feedback..." -ForegroundColor Yellow
    $feedback = @{
        accepted = $true
        rating = 5
    } | ConvertTo-Json
    try {
        $result = Invoke-RestMethod -Uri "$baseUrl/api/v1/synergies/$synergyId/feedback" -Method Post -Body $feedback -ContentType "application/json"
        Write-Host "✅ Feedback submitted" -ForegroundColor Green
    } catch {
        Write-Host "⚠️ Feedback submission failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }
} else {
    Write-Host "No synergies found - run pattern analysis first" -ForegroundColor Yellow
}

# 5. Get patterns
Write-Host "`n5. Getting Patterns..." -ForegroundColor Yellow
$patterns = Invoke-RestMethod -Uri "$baseUrl/api/v1/patterns/list?limit=5"
Write-Host "Found $($patterns.data.count) patterns" -ForegroundColor Green

# 6. Get statistics
Write-Host "`n6. Getting Statistics..." -ForegroundColor Yellow
$stats = Invoke-RestMethod -Uri "$baseUrl/api/v1/synergies/statistics"
Write-Host "Total synergies: $($stats.data.total_synergies)" -ForegroundColor Green

Write-Host "`n✅ All tests complete!" -ForegroundColor Green
```

Run it:
```powershell
.\test-recommendations.ps1
```

## Troubleshooting

### Service Not Running
```powershell
# Check if service is running
docker ps | Select-String "ai-pattern-service"

# Start service
docker-compose up -d ai-pattern-service

# Check logs
docker logs homeiq-ai-pattern-service
```

### Database Issues
```powershell
# Check database integrity
Invoke-RestMethod -Uri "http://localhost:8020/database/integrity"

# If corrupted, repair (if endpoint exists)
# Invoke-RestMethod -Uri "http://localhost:8020/api/v1/patterns/repair" -Method Post
```

### Home Assistant Not Configured
```powershell
# Set environment variables
$env:HA_URL = "http://your-ha-instance:8123"
$env:HA_TOKEN = "your-long-lived-access-token"

# Restart service
docker-compose restart ai-pattern-service
```

## Next Steps

1. **Run Pattern Analysis**: Trigger pattern detection to generate synergies
2. **Test Automation Generation**: Create automations from synergies
3. **Submit Feedback**: Provide feedback to improve pattern detection
4. **Monitor Evolution**: Watch patterns evolve over time
5. **Review Quality**: Use `tapps-agents` to verify code quality

## Related Documentation

- [Implementation Summary](PATTERNS_SYNERGIES_RECOMMENDATIONS_COMPLETE.md)
- [E2E Testing Guide](../services/ai-pattern-service/tests/E2E_TESTING_GUIDE.md)
- [API Documentation](../services/ai-pattern-service/docs/API_DOCUMENTATION.md)
