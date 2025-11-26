# Setup script for Home Assistant test container (PowerShell)
# Creates initial configuration and long-lived access token

$ErrorActionPreference = "Stop"

Write-Host "Setting up Home Assistant test container..." -ForegroundColor Cyan

# Wait for HA to be ready
Write-Host "Waiting for Home Assistant to be ready..." -ForegroundColor Yellow
$timeout = 300
$elapsed = 0
$ready = $false

while ($elapsed -lt $timeout) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8124/api/" -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Home Assistant is ready!" -ForegroundColor Green
            $ready = $true
            break
        }
    } catch {
        # Not ready yet
    }
    
    Write-Host "  Waiting... ($elapsed/$timeout seconds)" -ForegroundColor Gray
    Start-Sleep -Seconds 5
    $elapsed += 5
}

if (-not $ready) {
    Write-Host "❌ Timeout waiting for Home Assistant" -ForegroundColor Red
    exit 1
}

# Check if token already exists
if (Test-Path .env.test) {
    $envContent = Get-Content .env.test -Raw
    if ($envContent -match "HA_TEST_TOKEN") {
        Write-Host "✅ Test token already exists in .env.test" -ForegroundColor Green
        exit 0
    }
}

# Create long-lived access token
Write-Host "Creating long-lived access token..." -ForegroundColor Yellow

try {
    $body = @{
        name = "HomeIQ Test Token"
        client_name = "HomeIQ Test"
        type = "long_lived_access_token"
        lifespan = 3650
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri "http://localhost:8124/auth/providers/homeassistant/login" `
        -Method Post `
        -ContentType "application/json" `
        -Body $body `
        -ErrorAction Stop

    $token = $response.access_token

    if ([string]::IsNullOrEmpty($token)) {
        throw "Token is empty"
    }
} catch {
    Write-Host "⚠️  Could not create token automatically. Please create one manually:" -ForegroundColor Yellow
    Write-Host "   1. Open http://localhost:8124" -ForegroundColor White
    Write-Host "   2. Go to Profile → Long-Lived Access Tokens" -ForegroundColor White
    Write-Host "   3. Create token named 'HomeIQ Test Token'" -ForegroundColor White
    Write-Host "   4. Add to .env.test: HA_TEST_TOKEN=your_token_here" -ForegroundColor White
    exit 1
}

# Create .env.test file
$envContent = @"
# Home Assistant Test Configuration
HA_TEST_URL=http://localhost:8124
HA_TEST_TOKEN=$token
HA_TEST_WS_URL=ws://localhost:8124/api/websocket
INFLUXDB_TEST_BUCKET=home_assistant_events_test
"@

$envContent | Out-File -FilePath .env.test -Encoding utf8

Write-Host "✅ Test token created and saved to .env.test" -ForegroundColor Green
Write-Host "   Token: $($token.Substring(0, [Math]::Min(20, $token.Length)))..." -ForegroundColor Gray
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Review .env.test file" -ForegroundColor White
Write-Host "  2. Load test dataset: python scripts/load_dataset_to_ha.py --dataset assist-mini" -ForegroundColor White
Write-Host "  3. Run tests: pytest tests/datasets/ -v" -ForegroundColor White

