# Deploy Device Database Enhancement Services
# This script builds and starts the 5 new Device Database services

Write-Host "🚀 Deploying Device Database Enhancement Services..." -ForegroundColor Cyan

# Build new services
Write-Host "📦 Building new services..." -ForegroundColor Yellow
docker compose build device-health-monitor device-context-classifier device-setup-assistant device-database-client device-recommender

# Run database migration for data-api (adds new device fields)
Write-Host "🗄️  Running database migration..." -ForegroundColor Yellow
docker compose run --rm data-api alembic upgrade head

# Start new services
Write-Host "▶️  Starting new services..." -ForegroundColor Yellow
docker compose up -d device-health-monitor device-context-classifier device-setup-assistant device-database-client device-recommender

# Wait for services to be healthy
Write-Host "⏳ Waiting for services to be healthy..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Check service health
Write-Host "🏥 Checking service health..." -ForegroundColor Yellow
try {
    Invoke-WebRequest -Uri "http://localhost:8019/health" -UseBasicParsing | Out-Null
    Write-Host " ✅ device-health-monitor" -ForegroundColor Green
} catch {
    Write-Host " ❌ device-health-monitor" -ForegroundColor Red
}

try {
    Invoke-WebRequest -Uri "http://localhost:8032/health" -UseBasicParsing | Out-Null
    Write-Host " ✅ device-context-classifier" -ForegroundColor Green
} catch {
    Write-Host " ❌ device-context-classifier" -ForegroundColor Red
}

try {
    Invoke-WebRequest -Uri "http://localhost:8021/health" -UseBasicParsing | Out-Null
    Write-Host " ✅ device-setup-assistant" -ForegroundColor Green
} catch {
    Write-Host " ❌ device-setup-assistant" -ForegroundColor Red
}

try {
    Invoke-WebRequest -Uri "http://localhost:8022/health" -UseBasicParsing | Out-Null
    Write-Host " ✅ device-database-client" -ForegroundColor Green
} catch {
    Write-Host " ❌ device-database-client" -ForegroundColor Red
}

try {
    Invoke-WebRequest -Uri "http://localhost:8023/health" -UseBasicParsing | Out-Null
    Write-Host " ✅ device-recommender" -ForegroundColor Green
} catch {
    Write-Host " ❌ device-recommender" -ForegroundColor Red
}

Write-Host ""
Write-Host "✅ Device Database Enhancement Services deployed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Services available at:"
Write-Host "  - Device Health Monitor: http://localhost:8019"
Write-Host "  - Device Context Classifier: http://localhost:8032"
Write-Host "  - Device Setup Assistant: http://localhost:8021"
Write-Host "  - Device Database Client: http://localhost:8022"
Write-Host "  - Device Recommender: http://localhost:8023"
Write-Host ""
Write-Host "API endpoints available via Data API (http://localhost:8006):"
Write-Host "  - GET /api/devices/{device_id}/health"
Write-Host "  - POST /api/devices/{device_id}/classify"
Write-Host "  - GET /api/devices/{device_id}/setup-guide"
Write-Host "  - POST /api/devices/{device_id}/discover-capabilities"
Write-Host "  - GET /api/devices/recommendations"

