# Services Review Script
# Reviews all services using TappsCodingAgents

$services = @(
    "websocket-ingestion",
    "data-api",
    "admin-api",
    "ai-automation-service-new",
    "weather-api",
    "carbon-intensity-service",
    "air-quality-service",
    "calendar-service",
    "electricity-pricing-service",
    "ai-pattern-service",
    "ai-query-service",
    "ai-core-service",
    "ai-code-executor",
    "ai-training-service",
    "device-intelligence-service",
    "device-setup-assistant",
    "device-recommender",
    "device-health-monitor",
    "device-database-client",
    "device-context-classifier",
    "automation-miner",
    "energy-correlator",
    "data-retention",
    "ha-ai-agent-service",
    "ha-setup-service",
    "proactive-agent-service",
    "openvino-service",
    "ml-service",
    "log-aggregator",
    "smart-meter-service",
    "ha-simulator"
)

$results = @()

foreach ($service in $services) {
    $mainFile = "services\$service\src\main.py"
    
    # Check if file exists
    if (Test-Path $mainFile) {
        Write-Host "Reviewing $service..." -ForegroundColor Cyan
        try {
            $output = python -m tapps_agents.cli reviewer score $mainFile 2>&1
            $results += [PSCustomObject]@{
                Service = $service
                Status = "Reviewed"
                Output = $output
            }
        } catch {
            $results += [PSCustomObject]@{
                Service = $service
                Status = "Error"
                Output = $_.Exception.Message
            }
        }
    } else {
        Write-Host "Skipping $service - main.py not found" -ForegroundColor Yellow
    }
}

$results | Format-Table -AutoSize

