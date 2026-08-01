# Home Assistant Automation Checker
# This script checks all automations and their status

param(
    [string]$HA_URL = $env:HA_HTTP_URL,
    [string]$HA_TOKEN = $env:HA_TOKEN
)

if (-not $HA_URL) {
    Write-Error "HA_URL is not set. Pass -HA_URL or set HA_HTTP_URL."
    exit 1
}
if (-not $HA_TOKEN) {
    Write-Error "HA_TOKEN is not set. Pass -HA_TOKEN or set HA_TOKEN."
    exit 1
}

Write-Host "🔍 Checking Home Assistant Automations..." -ForegroundColor Cyan
Write-Host "HA URL: $HA_URL" -ForegroundColor Gray
Write-Host ""

try {
    # Get all states
    $response = Invoke-WebRequest -Uri "$HA_URL/api/states" -Headers @{"Authorization"="Bearer $HA_TOKEN"} -UseBasicParsing
    $states = $response.Content | ConvertFrom-Json
    
    # Filter for automations
    $automations = $states | Where-Object {$_.entity_id -like "automation.*"}
    
    if ($automations.Count -eq 0) {
        Write-Host "❌ No automations found!" -ForegroundColor Red
        return
    }
    
    Write-Host "📋 Found $($automations.Count) automation(s):" -ForegroundColor Green
    Write-Host ""
    
    foreach ($automation in $automations) {
        $status = if ($automation.state -eq "on") { "✅ ACTIVE" } else { "❌ INACTIVE" }
        $statusColor = if ($automation.state -eq "on") { "Green" } else { "Red" }
        
        $friendlyName = $automation.attributes.friendly_name
        $lastTriggered = $automation.attributes.last_triggered
        $lastChanged = $automation.last_changed
        
        Write-Host "🤖 $($automation.entity_id)" -ForegroundColor Yellow
        Write-Host "   Name: $friendlyName" -ForegroundColor White
        Write-Host "   Status: $status" -ForegroundColor $statusColor
        Write-Host "   Last Triggered: $lastTriggered" -ForegroundColor Gray
        Write-Host "   Last Changed: $lastChanged" -ForegroundColor Gray
        Write-Host ""
    }
    
    # Ask if user wants to see YAML for specific automation
    Write-Host "🔧 Would you like to see the YAML for a specific automation?" -ForegroundColor Cyan
    $choice = Read-Host "Enter automation ID (e.g., automation.test) or press Enter to skip"
    
    if ($choice -and $choice -like "automation.*") {
        try {
            Write-Host "📄 Fetching YAML for $choice..." -ForegroundColor Cyan
            $yamlResponse = Invoke-WebRequest -Uri "$HA_URL/api/config/automation/config/$choice" -Headers @{"Authorization"="Bearer $HA_TOKEN"} -UseBasicParsing
            Write-Host "YAML Configuration:" -ForegroundColor Green
            Write-Host $yamlResponse.Content -ForegroundColor White
        }
        catch {
            Write-Host "❌ Error fetching YAML: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    
}
catch {
    Write-Host "❌ Error connecting to Home Assistant: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Please check:" -ForegroundColor Yellow
    Write-Host "  - HA URL is correct: $HA_URL" -ForegroundColor Gray
    Write-Host "  - HA Token is valid" -ForegroundColor Gray
    Write-Host "  - Home Assistant is running" -ForegroundColor Gray
}
