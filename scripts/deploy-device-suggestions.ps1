# Deploy Device-Based Automation Suggestions Feature
# PowerShell script for Windows

$ErrorActionPreference = "Stop"

Write-Host "🚀 Deploying Device-Based Automation Suggestions Feature..." -ForegroundColor Blue
Write-Host ""

# Check if docker-compose is available
try {
    $null = Get-Command docker -ErrorAction Stop
} catch {
    Write-Host "❌ Docker not found. Please install Docker Desktop." -ForegroundColor Red
    exit 1
}

# Get project root
$ProjectRoot = if ($PSScriptRoot) { 
    Split-Path -Parent $PSScriptRoot 
} else { 
    $PWD 
}

Set-Location $ProjectRoot

Write-Host "📋 Services to update:" -ForegroundColor Blue
Write-Host "  1. ha-ai-agent-service (new device suggestions endpoint)" -ForegroundColor White
Write-Host "  2. ai-automation-ui (new device picker and suggestions UI)" -ForegroundColor White
Write-Host ""

# Function to rebuild and restart a service
function Deploy-Service {
    param(
        [string]$ServiceName,
        [string]$Description
    )
    
    Write-Host "🔨 Rebuilding $Description..." -ForegroundColor Yellow
    
    # Build the service
    docker compose build $ServiceName
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to build $ServiceName" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "🔄 Restarting $Description..." -ForegroundColor Yellow
    
    # Stop, remove, and start the service
    docker compose stop $ServiceName 2>&1 | Out-Null
    docker compose up -d $ServiceName
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to start $ServiceName" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ $Description deployed successfully" -ForegroundColor Green
    Write-Host ""
}

# Check Docker is running
try {
    docker ps | Out-Null
    Write-Host "✅ Docker is running" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host "❌ Docker Desktop is not running!" -ForegroundColor Red
    Write-Host "   Please start Docker Desktop and try again." -ForegroundColor Yellow
    exit 1
}

# Deploy ha-ai-agent-service
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Blue
Write-Host "1/2: ha-ai-agent-service" -ForegroundColor Blue
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Blue
Deploy-Service "ha-ai-agent-service" "HA AI Agent Service"

# Deploy ai-automation-ui
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Blue
Write-Host "2/2: ai-automation-ui" -ForegroundColor Blue
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Blue
Deploy-Service "ai-automation-ui" "AI Automation UI"

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "✅ Deployment Complete!" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Check service logs: docker compose logs -f ha-ai-agent-service" -ForegroundColor White
Write-Host "  2. Check service health: Invoke-RestMethod -Uri 'http://localhost:8030/health'" -ForegroundColor White
Write-Host "  3. Test the feature: Navigate to http://localhost:3001/agent" -ForegroundColor White
Write-Host ""
