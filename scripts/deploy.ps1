# Production Deployment Script (PowerShell)
# HA Ingestor Production Deployment Automation

param(
    [Parameter(Position=0)]
    [ValidateSet("deploy", "validate", "status", "logs", "stop", "restart", "help")]
    [string]$Command = "deploy"
)

# Configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$Environment = if ($env:ENVIRONMENT) { $env:ENVIRONMENT } else { "production" }
$ComposeFile = "docker-compose.prod.yml"
$EnvFile = "infrastructure/env.production"

# Colors for output
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Error handling
function Exit-WithError {
    param([string]$Message)
    Write-Error $Message
    exit 1
}

# Check prerequisites
function Test-Prerequisites {
    Write-Info "Checking prerequisites..."
    
    # Check Docker
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Exit-WithError "Docker is not installed or not in PATH"
    }
    
    # Check Docker Compose
    $dockerComposeAvailable = (Get-Command docker-compose -ErrorAction SilentlyContinue) -or 
                             (docker compose version 2>$null)
    
    if (-not $dockerComposeAvailable) {
        Exit-WithError "Docker Compose is not installed or not in PATH"
    }
    
    # Check if we're in the right directory
    if (-not (Test-Path "$ProjectRoot/docker-compose.yml")) {
        Exit-WithError "Not in HA Ingestor project root directory"
    }
    
    # Check if environment file exists
    if (-not (Test-Path "$ProjectRoot/$EnvFile")) {
        Exit-WithError "Environment file not found: $EnvFile"
    }
    
    Write-Success "Prerequisites check passed"
}

# Validate environment configuration
function Test-Configuration {
    Write-Info "Validating environment configuration..."
    
    # Read environment variables
    $envVars = @{}
    if (Test-Path "$ProjectRoot/$EnvFile") {
        Get-Content "$ProjectRoot/$EnvFile" | ForEach-Object {
            if ($_ -match '^([^#][^=]+)=(.*)$') {
                $envVars[$matches[1]] = $matches[2]
            }
        }
    }
    
    # Check required variables
    $requiredVars = @(
        "HOME_ASSISTANT_URL",
        "HOME_ASSISTANT_TOKEN", 
        "INFLUXDB_PASSWORD",
        "INFLUXDB_TOKEN",
        "WEATHER_API_KEY",
        "JWT_SECRET_KEY",
        "ADMIN_PASSWORD"
    )
    
    $missingVars = @()
    
    foreach ($var in $requiredVars) {
        $value = $envVars[$var]
        if (-not $value -or $value -match "your_" -or $value -match "here$") {
            $missingVars += $var
        }
    }
    
    if ($missingVars.Count -gt 0) {
        Write-Error "Missing or invalid configuration variables:"
        foreach ($var in $missingVars) {
            Write-Error "  - $var"
        }
        Write-Error "Please update $EnvFile with proper values"
        exit 1
    }
    
    Write-Success "Configuration validation passed"
}

# Create necessary directories and volumes
function Initialize-Directories {
    Write-Info "Setting up directories and volumes..."
    
    # Create log directories
    $logDirs = @(
        "$ProjectRoot/logs/influxdb",
        "$ProjectRoot/logs/websocket-ingestion",
        "$ProjectRoot/logs/enrichment-pipeline",
        "$ProjectRoot/logs/weather-api",
        "$ProjectRoot/logs/admin-api",
        "$ProjectRoot/logs/data-retention",
        "$ProjectRoot/logs/dashboard",
        "$ProjectRoot/backups"
    )
    
    foreach ($dir in $logDirs) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
    }
    
    Write-Success "Directories setup completed"
}

# Pull latest images
function Invoke-PullImages {
    Write-Info "Pulling latest images..."
    
    Push-Location $ProjectRoot
    
    try {
        if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
            & docker-compose -f $ComposeFile --env-file $EnvFile pull
        } else {
            & docker compose -f $ComposeFile --env-file $EnvFile pull
        }
        Write-Success "Images pulled successfully"
    }
    finally {
        Pop-Location
    }
}

# Build custom images
function Invoke-BuildImages {
    Write-Info "Building custom images..."
    
    Push-Location $ProjectRoot
    
    try {
        if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
            & docker-compose -f $ComposeFile --env-file $EnvFile build --no-cache
        } else {
            & docker compose -f $ComposeFile --env-file $EnvFile build --no-cache
        }
        Write-Success "Images built successfully"
    }
    finally {
        Pop-Location
    }
}

# Deploy services
function Invoke-DeployServices {
    Write-Info "Deploying services..."
    
    Push-Location $ProjectRoot
    
    try {
        # Stop existing services gracefully
        Write-Info "Stopping existing services..."
        if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
            & docker-compose -f $ComposeFile --env-file $EnvFile down --timeout 30
        } else {
            & docker compose -f $ComposeFile --env-file $EnvFile down --timeout 30
        }
        
        # Start services
        Write-Info "Starting services..."
        if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
            & docker-compose -f $ComposeFile --env-file $EnvFile up -d
        } else {
            & docker compose -f $ComposeFile --env-file $EnvFile up -d
        }
        
        Write-Success "Services deployed successfully"
    }
    finally {
        Pop-Location
    }
}

# Wait for services to be healthy
function Wait-ForHealth {
    Write-Info "Waiting for services to be healthy..."
    
    $services = @(
        "influxdb",
        "websocket-ingestion", 
        "enrichment-pipeline",
        "admin-api",
        "data-retention",
        "health-dashboard"
    )
    
    $maxAttempts = 30
    
    foreach ($service in $services) {
        Write-Info "Checking health of $service..."
        $attempt = 1
        
        do {
            Push-Location $ProjectRoot
            
            try {
                $healthStatus = "unknown"
                if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
                    $containerId = & docker-compose -f $ComposeFile --env-file $EnvFile ps -q $service
                    if ($containerId) {
                        $healthStatus = docker inspect --format='{{.State.Health.Status}}' $containerId 2>$null
                    }
                } else {
                    $containerId = & docker compose -f $ComposeFile --env-file $EnvFile ps -q $service
                    if ($containerId) {
                        $healthStatus = docker inspect --format='{{.State.Health.Status}}' $containerId 2>$null
                    }
                }
                
                if ($healthStatus -eq "healthy") {
                    Write-Success "$service is healthy"
                    break
                } elseif ($attempt -eq $maxAttempts) {
                    Write-Warning "$service health check timed out (status: $healthStatus)"
                } else {
                    Write-Info "$service health status: $healthStatus (attempt $attempt/$maxAttempts)"
                    Start-Sleep -Seconds 10
                }
            }
            finally {
                Pop-Location
            }
            
            $attempt++
        } while ($attempt -le $maxAttempts)
    }
}

# Run post-deployment tests
function Invoke-PostDeploymentTests {
    Write-Info "Running post-deployment tests..."
    
    # Test API key validation
    if (Test-Path "$ProjectRoot/tests/test_api_keys.py") {
        Write-Info "Running API key validation tests..."
        Push-Location $ProjectRoot
        
        try {
            & python tests/test_api_keys.py --env-file $EnvFile --output json | Out-File -FilePath "deployment_test_results.json" -Encoding UTF8
            
            if ($LASTEXITCODE -eq 0) {
                Write-Success "API key validation tests passed"
            } else {
                Write-Warning "API key validation tests failed - check deployment_test_results.json"
            }
        }
        finally {
            Pop-Location
        }
    }
    
    # Test service connectivity
    Write-Info "Testing service connectivity..."
    
    $endpoints = @(
        @{Url="http://localhost:8086/health"; Service="InfluxDB"},
        @{Url="http://localhost:8001/health"; Service="WebSocket Ingestion"},
        @{Url="http://localhost:8002/health"; Service="Enrichment Pipeline"},
        @{Url="http://localhost:8003/api/v1/health"; Service="Admin API"},
        @{Url="http://localhost:8080/health"; Service="Data Retention"},
        @{Url="http://localhost:3000"; Service="Health Dashboard"}
    )
    
    foreach ($endpoint in $endpoints) {
        try {
            $response = Invoke-WebRequest -Uri $endpoint.Url -TimeoutSec 10 -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                Write-Success "$($endpoint.Service) is accessible"
            }
        }
        catch {
            Write-Warning "$($endpoint.Service) is not accessible at $($endpoint.Url)"
        }
    }
    
    Write-Success "Post-deployment tests completed"
}

# Show deployment status
function Show-Status {
    Write-Info "Deployment Status:"
    
    Push-Location $ProjectRoot
    
    try {
        if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
            & docker-compose -f $ComposeFile --env-file $EnvFile ps
        } else {
            & docker compose -f $ComposeFile --env-file $EnvFile ps
        }
    }
    finally {
        Pop-Location
    }
    
    Write-Host ""
    Write-Info "Service URLs:"
    Write-Host "  - InfluxDB: http://localhost:8086"
    Write-Host "  - WebSocket Ingestion: http://localhost:8001"
    Write-Host "  - Admin API: http://localhost:8003"
    Write-Host "  - Data Retention: http://localhost:8080"
    Write-Host "  - Health Dashboard: http://localhost:3000"
    
    Write-Host ""
    Write-Info "Logs can be viewed with:"
    Write-Host "  - All services: docker-compose -f $ComposeFile logs -f"
    Write-Host "  - Specific service: docker-compose -f $ComposeFile logs -f <service-name>"
}

# Main deployment function
function Invoke-MainDeployment {
    Write-Info "Starting HA Ingestor Production Deployment"
    Write-Info "Environment: $Environment"
    Write-Info "Compose file: $ComposeFile"
    Write-Info "Environment file: $EnvFile"
    
    Test-Prerequisites
    Test-Configuration
    Initialize-Directories
    Invoke-PullImages
    Invoke-BuildImages
    Invoke-DeployServices
    Wait-ForHealth
    Invoke-PostDeploymentTests
    Show-Status
    
    Write-Success "Production deployment completed successfully!"
    
    Write-Host ""
    Write-Info "Next steps:"
    Write-Host "  1. Verify all services are running: docker-compose -f $ComposeFile ps"
    Write-Host "  2. Check logs: docker-compose -f $ComposeFile logs -f"
    Write-Host "  3. Access the health dashboard: http://localhost:3000"
    Write-Host "  4. Test API endpoints: http://localhost:8003/api/v1/health"
}

# Handle script commands
switch ($Command) {
    "deploy" {
        Invoke-MainDeployment
    }
    "validate" {
        Test-Prerequisites
        Test-Configuration
        Write-Success "Configuration validation completed"
    }
    "status" {
        Show-Status
    }
    "logs" {
        Push-Location $ProjectRoot
        try {
            if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
                & docker-compose -f $ComposeFile --env-file $EnvFile logs -f
            } else {
                & docker compose -f $ComposeFile --env-file $EnvFile logs -f
            }
        }
        finally {
            Pop-Location
        }
    }
    "stop" {
        Push-Location $ProjectRoot
        try {
            if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
                & docker-compose -f $ComposeFile --env-file $EnvFile down
            } else {
                & docker compose -f $ComposeFile --env-file $EnvFile down
            }
            Write-Success "Services stopped"
        }
        finally {
            Pop-Location
        }
    }
    "restart" {
        Push-Location $ProjectRoot
        try {
            if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
                & docker-compose -f $ComposeFile --env-file $EnvFile restart
            } else {
                & docker compose -f $ComposeFile --env-file $EnvFile restart
            }
            Write-Success "Services restarted"
        }
        finally {
            Pop-Location
        }
    }
    "help" {
        Write-Host "HA Ingestor Production Deployment Script"
        Write-Host ""
        Write-Host "Usage: .\deploy.ps1 [command]"
        Write-Host ""
        Write-Host "Commands:"
        Write-Host "  deploy    Deploy all services (default)"
        Write-Host "  validate  Validate configuration only"
        Write-Host "  status    Show deployment status"
        Write-Host "  logs      Show service logs"
        Write-Host "  stop      Stop all services"
        Write-Host "  restart   Restart all services"
        Write-Host "  help      Show this help message"
    }
}
