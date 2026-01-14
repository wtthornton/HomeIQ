# Diagnostic Script for Automation Mismatch Issue
# Tests connection between HA AutomateAI and Home Assistant

Write-Host "🔍 Diagnosing Automation Mismatch Issue..." -ForegroundColor Cyan
Write-Host ""

# Check if .env file exists
if (Test-Path ".env") {
    Write-Host "✅ .env file found" -ForegroundColor Green
    $envContent = Get-Content ".env" -Raw
    
    # Check for required variables
    $hasUrl = $envContent -match "HOME_ASSISTANT_URL|HA_URL"
    $hasToken = $envContent -match "HOME_ASSISTANT_TOKEN|HA_TOKEN"
    
    if ($hasUrl) {
        Write-Host "✅ Home Assistant URL configured" -ForegroundColor Green
    } else {
        Write-Host "❌ Home Assistant URL NOT configured in .env" -ForegroundColor Red
    }
    
    if ($hasToken) {
        Write-Host "✅ Home Assistant Token configured" -ForegroundColor Green
    } else {
        Write-Host "❌ Home Assistant Token NOT configured in .env" -ForegroundColor Red
        Write-Host "   Add: HOME_ASSISTANT_TOKEN=your-token-here" -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ .env file not found" -ForegroundColor Red
}

Write-Host ""

# Check if service is running
Write-Host "📦 Checking service status..." -ForegroundColor Cyan
$serviceRunning = docker ps --filter "name=ai-automation-service-new" --format "{{.Names}}" | Select-String "ai-automation-service-new"

if ($serviceRunning) {
    Write-Host "✅ ai-automation-service-new is running" -ForegroundColor Green
    
    # Check environment variables in container
    Write-Host ""
    Write-Host "🔧 Checking container environment variables..." -ForegroundColor Cyan
    $containerEnv = docker exec ai-automation-service-new env 2>$null | Select-String "HA_"
    
    if ($containerEnv) {
        Write-Host "✅ Environment variables found in container:" -ForegroundColor Green
        $containerEnv | ForEach-Object { Write-Host "   $_" -ForegroundColor Gray }
    } else {
        Write-Host "❌ No HA_* environment variables found in container" -ForegroundColor Red
    }
    
    # Check service logs for errors
    Write-Host ""
    Write-Host "📋 Checking recent service logs..." -ForegroundColor Cyan
    $logs = docker logs ai-automation-service-new --tail 20 2>&1
    
    if ($logs -match "Home Assistant.*not configured") {
        Write-Host "❌ Service logs show: Home Assistant not configured" -ForegroundColor Red
    } elseif ($logs -match "Failed to list automations") {
        Write-Host "❌ Service logs show: Failed to list automations" -ForegroundColor Red
        Write-Host "   Check logs for connection errors" -ForegroundColor Yellow
    } elseif ($logs -match "Successfully fetched.*automations") {
        Write-Host "✅ Service successfully fetched automations" -ForegroundColor Green
    } else {
        Write-Host "⚠️  No clear status in logs" -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ ai-automation-service-new is NOT running" -ForegroundColor Red
    Write-Host "   Start with: docker-compose up -d ai-automation-service-new" -ForegroundColor Yellow
}

Write-Host ""

# Test Home Assistant API directly (if token available)
Write-Host "🌐 Testing Home Assistant API connection..." -ForegroundColor Cyan

# Try to get token from .env
$token = $null
if (Test-Path ".env") {
    $envLines = Get-Content ".env"
    foreach ($line in $envLines) {
        if ($line -match "HOME_ASSISTANT_TOKEN\s*=\s*(.+)") {
            $token = $matches[1].Trim()
            break
        } elseif ($line -match "HA_TOKEN\s*=\s*(.+)") {
            $token = $matches[1].Trim()
            break
        }
    }
}

$haUrl = "http://192.168.1.86:8123"

if ($token) {
    try {
        $headers = @{
            "Authorization" = "Bearer $token"
            "Content-Type" = "application/json"
        }
        
        $response = Invoke-RestMethod -Uri "$haUrl/api/config/automation/config" -Headers $headers -ErrorAction Stop
        $count = if ($response -is [Array]) { $response.Count } else { 0 }
        
        Write-Host "✅ Successfully connected to Home Assistant" -ForegroundColor Green
        Write-Host "   Found $count automations" -ForegroundColor Green
        
        if ($count -gt 0) {
            Write-Host ""
            Write-Host "📋 Automations in Home Assistant:" -ForegroundColor Cyan
            foreach ($automation in $response) {
                $name = $automation.alias -or $automation.id -or "Unknown"
                $state = if ($automation.enabled) { "enabled" } else { "disabled" }
                Write-Host "   - $name ($state)" -ForegroundColor Gray
            }
        }
    } catch {
        Write-Host "❌ Failed to connect to Home Assistant API" -ForegroundColor Red
        Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Yellow
        
        if ($_.Exception.Response.StatusCode -eq 401) {
            Write-Host "   ⚠️  Authentication failed - token may be invalid or expired" -ForegroundColor Yellow
        } elseif ($_.Exception.Response.StatusCode -eq 404) {
            Write-Host "   ⚠️  API endpoint not found - check Home Assistant version" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "⚠️  Cannot test API - token not found in .env" -ForegroundColor Yellow
    Write-Host "   Add HOME_ASSISTANT_TOKEN to .env to enable API testing" -ForegroundColor Yellow
}

Write-Host ""

# Test service API endpoint
Write-Host "🔌 Testing HA AutomateAI service API..." -ForegroundColor Cyan
try {
    $serviceResponse = Invoke-RestMethod -Uri "http://localhost:8036/api/deploy/automations" -ErrorAction Stop
    $serviceCount = if ($serviceResponse.automations) { $serviceResponse.automations.Count } else { 0 }
    
    Write-Host "✅ Service API responded successfully" -ForegroundColor Green
    Write-Host "   Service reports $serviceCount automations" -ForegroundColor Green
    
    if ($serviceCount -eq 0) {
        Write-Host "   ⚠️  Service shows 0 automations (this is the mismatch!)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Failed to connect to service API" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "   Is the service running on port 8036?" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "📝 Summary:" -ForegroundColor Cyan
Write-Host "   1. Check .env file has HOME_ASSISTANT_TOKEN configured" -ForegroundColor White
Write-Host "   2. Restart service: docker-compose restart ai-automation-service-new" -ForegroundColor White
Write-Host "   3. Check service logs: docker logs ai-automation-service-new --tail 50" -ForegroundColor White
Write-Host ""
Write-Host "📄 See implementation/AUTOMATION_MISMATCH_DIAGNOSIS.md for detailed fix steps" -ForegroundColor Cyan
