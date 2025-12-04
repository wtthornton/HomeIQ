# Deploy YAML Validation Consolidation Changes
# PowerShell script for Windows

$ErrorActionPreference = "Stop"

Write-Host "🚀 Deploying YAML Validation Consolidation Changes..." -ForegroundColor Blue
Write-Host ""

# Check if docker-compose is available
try {
    $null = Get-Command docker-compose -ErrorAction Stop
} catch {
    Write-Host "❌ docker-compose not found. Please install docker-compose." -ForegroundColor Red
    exit 1
}

# Get project root (parent of scripts directory)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Set-Location $ProjectRoot

Write-Host "📋 Services to update:" -ForegroundColor Blue
Write-Host "  1. ai-automation-service (new validation router)"
Write-Host "  2. ha-ai-agent-service (new client, updated validation)"
Write-Host "  3. ai-automation-ui (updated API and Deployed page)"
Write-Host ""

# Function to rebuild and restart a service
function Rebuild-Service {
    param(
        [string]$ServiceName,
        [string]$Description
    )
    
    Write-Host "🔨 Rebuilding $Description..." -ForegroundColor Yellow
    
    docker-compose build --no-cache $ServiceName
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to build $ServiceName" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ $Description rebuilt successfully" -ForegroundColor Green
    Write-Host ""
}

# Function to restart a service
function Restart-Service {
    param(
        [string]$ServiceName,
        [string]$Description
    )
    
    Write-Host "🔄 Restarting $Description..." -ForegroundColor Yellow
    
    docker-compose restart $ServiceName
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to restart $ServiceName" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ $Description restarted successfully" -ForegroundColor Green
    Write-Host ""
}

# Function to stop, rebuild, and start a service
function Stop-Rebuild-Start {
    param(
        [string]$ServiceName,
        [string]$Description
    )
    
    Write-Host "🛑 Stopping $Description..." -ForegroundColor Yellow
    docker-compose stop $ServiceName
    
    Rebuild-Service -ServiceName $ServiceName -Description $Description
    
    Write-Host "🚀 Starting $Description..." -ForegroundColor Yellow
    docker-compose up -d $ServiceName
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to start $ServiceName" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ $Description started successfully" -ForegroundColor Green
    Write-Host ""
}

# Deploy ai-automation-service
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Blue
Write-Host "1/3: ai-automation-service" -ForegroundColor Blue
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Blue

$ValidationRouterPath = "services/ai-automation-service/src/api/yaml_validation_router.py"
if (Test-Path $ValidationRouterPath) {
    Write-Host "New validation router detected - rebuilding service..."
    Stop-Rebuild-Start -ServiceName "ai-automation-service" -Description "AI Automation Service"
} else {
    Write-Host "Source code is mounted - restarting service..."
    Restart-Service -ServiceName "ai-automation-service" -Description "AI Automation Service"
}

# Deploy ha-ai-agent-service
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Blue
Write-Host "2/3: ha-ai-agent-service" -ForegroundColor Blue
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Blue
Stop-Rebuild-Start -ServiceName "ha-ai-agent-service" -Description "HA AI Agent Service"

# Deploy ai-automation-ui
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Blue
Write-Host "3/3: ai-automation-ui" -ForegroundColor Blue
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Blue
Stop-Rebuild-Start -ServiceName "ai-automation-ui" -Description "AI Automation UI"

# Wait for services to be healthy
Write-Host "⏳ Waiting for services to be healthy..." -ForegroundColor Blue
Start-Sleep -Seconds 5

# Check service health
Write-Host ""
Write-Host "🔍 Checking service health..." -ForegroundColor Blue
docker-compose ps | Select-String -Pattern "(ai-automation-service|ha-ai-agent-service|ai-automation-ui)"

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "✅ Deployment Complete!" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host ""
Write-Host "Services deployed:"
Write-Host "  • ai-automation-service - http://localhost:8024"
Write-Host "  • ha-ai-agent-service - http://localhost:8030"
Write-Host "  • ai-automation-ui - http://localhost:3001"
Write-Host ""
Write-Host "Check logs with:"
Write-Host "  docker-compose logs -f ai-automation-service"
Write-Host "  docker-compose logs -f ha-ai-agent-service"
Write-Host "  docker-compose logs -f ai-automation-ui"
Write-Host ""

