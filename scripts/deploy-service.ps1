# Deploy Service Script
# General-purpose deployment script for HomeIQ services
# Usage: .\scripts\deploy-service.ps1 -ServiceName <service> [-Action <rebuild|restart|redeploy>] [-WaitForHealthy] [-CheckLogs]

param(
    [Parameter(Mandatory=$true)]
    [string[]]$ServiceName,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("rebuild", "restart", "redeploy")]
    [string]$Action = "redeploy",
    
    [switch]$WaitForHealthy,
    [switch]$CheckLogs,
    [switch]$NoCache,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Info { param([string]$Message) Write-Host $Message -ForegroundColor Cyan }
function Write-Success { param([string]$Message) Write-Host $Message -ForegroundColor Green }
function Write-Warning { param([string]$Message) Write-Host $Message -ForegroundColor Yellow }
function Write-Error { param([string]$Message) Write-Host $Message -ForegroundColor Red }
function Write-Step { param([string]$Message) Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Blue; Write-Host $Message -ForegroundColor Blue; Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Blue }

# Get project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

# Check prerequisites
Write-Info "Checking prerequisites..."

try {
    $null = Get-Command docker-compose -ErrorAction Stop
    Write-Success "✓ docker-compose found"
} catch {
    Write-Error "❌ docker-compose not found. Please install Docker Compose."
    exit 1
}

try {
    $null = Get-Command docker -ErrorAction Stop
    Write-Success "✓ docker found"
} catch {
    Write-Error "❌ docker not found. Please install Docker."
    exit 1
}

# Verify docker-compose.yml exists
if (-not (Test-Path "docker-compose.yml")) {
    Write-Error "❌ docker-compose.yml not found in project root"
    exit 1
}

Write-Success "✓ docker-compose.yml found"
Write-Host ""

# Function to get service description from docker-compose
function Get-ServiceDescription {
    param([string]$Service)
    
    # Map service names to descriptions
    $serviceDescriptions = @{
        "ai-pattern-service" = "AI Pattern Service"
        "ha-ai-agent-service" = "HA AI Agent Service"
        "api-automation-edge" = "API Automation Edge"
        "websocket-ingestion" = "WebSocket Ingestion"
        "data-api" = "Data API"
        "admin-api" = "Admin API"
        "ai-automation-service-new" = "AI Automation Service"
        "ai-automation-ui" = "AI Automation UI"
        "health-dashboard" = "Health Dashboard"
        "device-intelligence-service" = "Device Intelligence Service"
        "yaml-validation-service" = "YAML Validation Service"
        "blueprint-suggestion-service" = "Blueprint Suggestion Service"
        "proactive-agent-service" = "Proactive Agent Service"
    }
    
    return $serviceDescriptions[$Service] ?? $Service
}

# Function to check if service exists in docker-compose
function Test-ServiceExists {
    param([string]$Service)
    
    $services = docker-compose config --services 2>$null
    return $services -contains $Service
}

# Function to get service status
function Get-ServiceStatus {
    param([string]$Service)
    
    $status = docker-compose ps --format json $Service 2>$null | ConvertFrom-Json
    return $status
}

# Function to wait for service to be healthy
function Wait-ForHealthy {
    param(
        [string]$Service,
        [int]$MaxWaitSeconds = 120,
        [int]$IntervalSeconds = 5
    )
    
    Write-Info "⏳ Waiting for $Service to be healthy (max $MaxWaitSeconds seconds)..."
    
    $elapsed = 0
    while ($elapsed -lt $MaxWaitSeconds) {
        Start-Sleep -Seconds $IntervalSeconds
        $elapsed += $IntervalSeconds
        
        $status = Get-ServiceStatus -Service $Service
        if ($status -and $status.Health -eq "healthy") {
            Write-Success "✓ $Service is healthy!"
            return $true
        }
        
        if ($Verbose) {
            $state = "not found"
            $health = "unknown"
            if ($status) {
                $state = $status.State
                $health = $status.Health
            }
            Write-Host "  Status: $state, Health: $health ($elapsed/$MaxWaitSeconds seconds)" -ForegroundColor Gray
        }
    }
    
    Write-Warning "⚠ $Service did not become healthy within $MaxWaitSeconds seconds"
    return $false
}

# Function to rebuild service
function Rebuild-Service {
    param(
        [string]$Service,
        [string]$Description,
        [bool]$UseCache = $true
    )
    
    Write-Info "🔨 Rebuilding $Description..."
    
    $buildArgs = @($Service)
    if (-not $UseCache -or $NoCache) {
        $buildArgs += "--no-cache"
        Write-Info "  Building without cache..."
    }
    
    docker-compose build @buildArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "❌ Failed to build $Service"
        return $false
    }
    
    Write-Success "✓ $Description rebuilt successfully"
    return $true
}

# Function to restart service
function Restart-Service {
    param(
        [string]$Service,
        [string]$Description
    )
    
    Write-Info "🔄 Restarting $Description..."
    
    docker-compose restart $Service
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "❌ Failed to restart $Service"
        return $false
    }
    
    Write-Success "✓ $Description restarted successfully"
    return $true
}

# Function to stop service
function Stop-Service {
    param(
        [string]$Service,
        [string]$Description
    )
    
    Write-Info "🛑 Stopping $Description..."
    
    docker-compose stop $Service
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "❌ Failed to stop $Service"
        return $false
    }
    
    Write-Success "✓ $Description stopped"
    return $true
}

# Function to start service
function Start-Service {
    param(
        [string]$Service,
        [string]$Description
    )
    
    Write-Info "🚀 Starting $Description..."
    
    docker-compose up -d $Service
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "❌ Failed to start $Service"
        return $false
    }
    
    Write-Success "✓ $Description started"
    return $true
}

# Function to redeploy service (stop, rebuild, start)
function Redeploy-Service {
    param(
        [string]$Service,
        [string]$Description,
        [bool]$UseCache = $true
    )
    
    Write-Step "Deploying: $Description ($Service)"
    
    # Stop service
    if (-not (Stop-Service -Service $Service -Description $Description)) {
        return $false
    }
    
    # Rebuild service
    if (-not (Rebuild-Service -Service $Service -Description $Description -UseCache $UseCache)) {
        return $false
    }
    
    # Start service
    if (-not (Start-Service -Service $Service -Description $Description)) {
        return $false
    }
    
    return $true
}

# Function to check service logs
function Show-ServiceLogs {
    param(
        [string]$Service,
        [int]$Lines = 50
    )
    
    Write-Info "📋 Showing last $Lines lines of logs for $Service..."
    Write-Host ""
    
    docker-compose logs --tail $Lines $Service
    
    Write-Host ""
}

# Function to show service status
function Show-ServiceStatus {
    param([string[]]$Services)
    
    Write-Info "📊 Service Status:"
    Write-Host ""
    
    foreach ($service in $Services) {
        $status = Get-ServiceStatus -Service $service
        
        if ($status) {
            $state = $status.State
            $health = $status.Health
            $uptime = "unknown"
            if ($status.Status) { 
                $uptime = $status.Status -replace '.*Up ', '' 
            }
            
            $stateColor = switch ($state) {
                "running" { "Green" }
                "exited" { "Red" }
                default { "Yellow" }
            }
            
            $healthColor = switch ($health) {
                "healthy" { "Green" }
                "unhealthy" { "Red" }
                default { "Yellow" }
            }
            
            Write-Host "  $service" -ForegroundColor Cyan
            Write-Host "    State:  " -NoNewline
            Write-Host $state -ForegroundColor $stateColor
            Write-Host "    Health: " -NoNewline
            Write-Host $health -ForegroundColor $healthColor
            Write-Host "    Uptime: $uptime"
            Write-Host ""
        } else {
            Write-Warning "  $service - Status not available"
            Write-Host ""
        }
    }
}

# Main execution
Write-Step "HomeIQ Service Deployment Script"
Write-Host ""
Write-Info "Configuration:"
Write-Host ("  Services:    " + ($ServiceName -join ", "))
Write-Host "  Action:      $Action"
Write-Host "  Wait Healthy: $WaitForHealthy"
Write-Host "  Check Logs:  $CheckLogs"
Write-Host "  No Cache:    $NoCache"
Write-Host ""

# Validate services exist
$validServices = @()
$invalidServices = @()

foreach ($service in $ServiceName) {
    if (Test-ServiceExists -Service $service) {
        $validServices += $service
    } else {
        $invalidServices += $service
    }
}

if ($invalidServices.Count -gt 0) {
    Write-Error "❌ The following services were not found in docker-compose.yml:"
    foreach ($service in $invalidServices) {
        Write-Host "    • $service" -ForegroundColor Red
    }
    Write-Host ""
    Write-Info "Available services:"
    docker-compose config --services | ForEach-Object { Write-Host "    • $_" -ForegroundColor Gray }
    exit 1
}

# Show current status
Write-Step "Current Service Status"
Show-ServiceStatus -Services $validServices

# Deploy services
$deploymentResults = @{}

foreach ($service in $validServices) {
    $description = Get-ServiceDescription -Service $service
    
    $success = switch ($Action) {
        "rebuild" {
            Rebuild-Service -Service $service -Description $description -UseCache (-not $NoCache)
        }
        "restart" {
            Restart-Service -Service $service -Description $description
        }
        "redeploy" {
            Redeploy-Service -Service $service -Description $description -UseCache (-not $NoCache)
        }
    }
    
    $deploymentResults[$service] = $success
    
    if ($success) {
        # Wait for healthy if requested
        if ($WaitForHealthy) {
            Wait-ForHealthy -Service $service | Out-Null
        } else {
            # Small delay to allow service to start
            Start-Sleep -Seconds 2
        }
        
        # Show logs if requested
        if ($CheckLogs) {
            Show-ServiceLogs -Service $service
        }
    }
    
    Write-Host ""
}

# Final status
Write-Step "Deployment Complete - Final Status"
Show-ServiceStatus -Services $validServices

# Summary
$successful = ($deploymentResults.Values | Where-Object { $_ -eq $true }).Count
$failed = ($deploymentResults.Values | Where-Object { $_ -eq $false }).Count

Write-Host ""
if ($failed -eq 0) {
    Write-Success "✅ All services deployed successfully ($successful/$validServices.Count)"
} else {
    Write-Warning "⚠ Some services failed to deploy ($successful succeeded, $failed failed)"
    Write-Host ""
    Write-Error "Failed services:"
    foreach ($service in $deploymentResults.Keys) {
        if (-not $deploymentResults[$service]) {
            Write-Host "    • $service" -ForegroundColor Red
        }
    }
    exit 1
}

# Quick reference
Write-Host ""
Write-Info "Quick Reference:"
Write-Host "  Check status:  docker-compose ps"
Write-Host "  View logs:     docker-compose logs -f $($validServices[0])"
Write-Host "  Health check:  docker-compose ps $($validServices[0])"

# Service-specific URLs (if applicable)
$serviceUrls = @{
    "health-dashboard" = "http://localhost:3000"
    "admin-api" = "http://localhost:8004"
    "data-api" = "http://localhost:8006"
    "websocket-ingestion" = "http://localhost:8001"
    "ai-automation-ui" = "http://localhost:3001"
    "ha-ai-agent-service" = "http://localhost:8030"
    "api-automation-edge" = "http://localhost:8041"
}

$hasUrls = $false
foreach ($service in $validServices) {
    if ($serviceUrls.ContainsKey($service)) {
        if (-not $hasUrls) {
            Write-Host ""
            Write-Info "Service URLs:"
            $hasUrls = $true
        }
        Write-Host "  $($service): $($serviceUrls[$service])" -ForegroundColor Gray
    }
}

Write-Host ""