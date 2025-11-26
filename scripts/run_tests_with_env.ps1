# PowerShell script to run pattern and synergy tests with environment variables
# Usage: .\scripts\run_tests_with_env.ps1

$env:HA_URL = "http://localhost:8123"
$env:HA_TOKEN = "test_token"
$env:MQTT_BROKER = "localhost"
$env:OPENAI_API_KEY = "test_key"

Write-Host "🧪 Running Pattern & Synergy Tests" -ForegroundColor Cyan
Write-Host "Environment variables set:" -ForegroundColor Yellow
Write-Host "  HA_URL=$env:HA_URL"
Write-Host "  HA_TOKEN=$env:HA_TOKEN"
Write-Host "  MQTT_BROKER=$env:MQTT_BROKER"
Write-Host "  OPENAI_API_KEY=$env:OPENAI_API_KEY"
Write-Host ""

# Change to service directory
Push-Location services/ai-automation-service

try {
    # Run synergy tests
    Write-Host "Running Synergy Tests..." -ForegroundColor Green
    python -m pytest tests/test_synergy_detector.py tests/test_synergy_crud.py tests/test_synergy_suggestion_generator.py -v --tb=short
    
    # Run ML pattern detector tests (if not skipped)
    Write-Host "`nRunning ML Pattern Detector Tests..." -ForegroundColor Green
    python -m pytest tests/test_ml_pattern_detectors.py -v --tb=short
    
    # Note: Dataset tests require actual datasets and InfluxDB
    Write-Host "`nNote: Dataset tests require:" -ForegroundColor Yellow
    Write-Host "  - home-assistant-datasets repository"
    Write-Host "  - InfluxDB running"
    Write-Host "  - Full environment setup"
    Write-Host "`nTo run dataset tests, use:" -ForegroundColor Yellow
    Write-Host "  pytest tests/datasets/test_pattern*.py tests/datasets/test_synergy*.py -v"
    
} finally {
    Pop-Location
}

Write-Host "`n✅ Test execution complete" -ForegroundColor Green

