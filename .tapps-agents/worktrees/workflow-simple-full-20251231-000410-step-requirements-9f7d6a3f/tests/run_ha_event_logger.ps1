# HA Event Logger Runner
# Simple script to run the HA event logger for baseline measurement

param(
    [string]$HaUrl = "ws://homeassistant.local:8123/api/websocket",
    [int]$DurationMinutes = 5,
    [string]$HaToken = $env:HA_ACCESS_TOKEN
)

Write-Host "🔍 HA Event Logger - Baseline Measurement Tool" -ForegroundColor Cyan
Write-Host "=" * 60

# Check if HA token is provided
if (-not $HaToken) {
    # Try to load from .env files
    $envFiles = @('.env', 'infrastructure\.env', 'infrastructure\env.production')
    $tokenFound = $false
    
    foreach ($envFile in $envFiles) {
        if (Test-Path $envFile) {
            Write-Host "📄 Found .env file: $envFile" -ForegroundColor Green
            $content = Get-Content $envFile
            foreach ($line in $content) {
                if ($line -match '^HOME_ASSISTANT_TOKEN=(.+)$') {
                    $HaToken = $matches[1].Trim('"').Trim("'")
                    $tokenFound = $true
                    Write-Host "✅ Found HOME_ASSISTANT_TOKEN in $envFile" -ForegroundColor Green
                    break
                }
            }
            if ($tokenFound) { break }
        }
    }
    
    if (-not $tokenFound) {
        Write-Host "❌ Error: Home Assistant token not found" -ForegroundColor Red
        Write-Host "💡 Options:" -ForegroundColor Yellow
        Write-Host "   1. Set environment variable: `$env:HA_ACCESS_TOKEN='your_token'" -ForegroundColor Yellow
        Write-Host "   2. Add HOME_ASSISTANT_TOKEN=your_token to .env file" -ForegroundColor Yellow
        Write-Host "   3. Pass as parameter: -HaToken 'your_token'" -ForegroundColor Yellow
        Write-Host "💡 Checked .env files: $($envFiles -join ', ')" -ForegroundColor Yellow
        exit 1
    }
}

# Set environment variables
$env:HA_WEBSOCKET_URL = $HaUrl
$env:HA_ACCESS_TOKEN = $HaToken
$env:LOG_DURATION_MINUTES = $DurationMinutes.ToString()

Write-Host "🔗 HA URL: $HaUrl" -ForegroundColor Green
Write-Host "⏱️  Duration: $DurationMinutes minutes" -ForegroundColor Green
Write-Host "📊 This will establish baseline event volume from your HA instance" -ForegroundColor Yellow
Write-Host ""

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "🐍 Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found. Please install Python 3.7+" -ForegroundColor Red
    exit 1
}

# Check if required packages are installed
Write-Host "📦 Checking dependencies..." -ForegroundColor Yellow
try {
    python -c "import aiohttp" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "📦 Installing aiohttp..." -ForegroundColor Yellow
        pip install aiohttp
    }
} catch {
    Write-Host "❌ Failed to check/install dependencies" -ForegroundColor Red
    exit 1
}

Write-Host "🚀 Starting HA Event Logger..." -ForegroundColor Green
Write-Host ""

# Run the event logger
python tests/ha_event_logger.py

Write-Host ""
Write-Host "✅ Event logging completed!" -ForegroundColor Green
Write-Host "📄 Check 'ha_events.log' for detailed logs" -ForegroundColor Yellow
