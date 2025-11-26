# Quick check for HA test token
$ErrorActionPreference = "Continue"

Write-Host "Checking for Home Assistant test token..." -ForegroundColor Cyan

# Check .env.test file
if (Test-Path .env.test) {
    $envContent = Get-Content .env.test -Raw
    if ($envContent -match "HA_TEST_TOKEN\s*=\s*([^\s]+)") {
        $token = $matches[1]
        Write-Host "✅ Token found in .env.test" -ForegroundColor Green
        Write-Host "   Token: $($token.Substring(0, [Math]::Min(20, $token.Length)))..." -ForegroundColor Gray
        return $true
    }
}

# Check environment variable
if ($env:HA_TEST_TOKEN) {
    Write-Host "✅ Token found in environment variable" -ForegroundColor Green
    Write-Host "   Token: $($env:HA_TEST_TOKEN.Substring(0, [Math]::Min(20, $env:HA_TEST_TOKEN.Length)))..." -ForegroundColor Gray
    return $true
}

Write-Host "❌ No token found" -ForegroundColor Red
Write-Host "`nPlease create a token:" -ForegroundColor Yellow
Write-Host "  1. Open http://localhost:8124" -ForegroundColor White
Write-Host "  2. Go to Profile → Long-Lived Access Tokens" -ForegroundColor White
Write-Host "  3. Create token named 'HomeIQ Test Token'" -ForegroundColor White
Write-Host "  4. Add to .env.test: HA_TEST_TOKEN=your_token_here" -ForegroundColor White
Write-Host "     Or set: `$env:HA_TEST_TOKEN='your_token_here'" -ForegroundColor White
return $false

